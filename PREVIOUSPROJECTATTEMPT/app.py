"""
Flask web app for the Construction Code Workspace.

This version is prepared for Azure App Service deployment and includes:
  - Microsoft Entra ID authentication via MSAL (see `auth/`)
  - Server-side sessions (filesystem) via Flask-Session

RAG-specific features (vectorstores, PDF serving, LLM) are implemented below and
will be progressively migrated to Azure services (Blob + Azure OpenAI).
"""

import os
import json
from functools import lru_cache

from flask import (
    Flask,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    stream_with_context,
    url_for,
    session,
)
from flask_session import Session
from werkzeug.middleware.proxy_fix import ProxyFix

from auth.config import init_auth
from auth.decorators import domain_required
from auth.routes import auth_bp


# non-community edition may not be supported by Azure
from langchain_community.embeddings import HuggingFaceEmbeddings


from llm.azure_openai import get_chat_model

from storage.blob import BlobSettings, BlobStorageClient
from rag.doc_index import build_doc_index_from_blob
from rag.vectorstores import VectorstoreManager, default_cache_dir

app = Flask(__name__)

# Respect proxy headers (Azure App Service sits behind a reverse proxy).
# This makes url_for(..., _external=True) generate correct https URLs.
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # type: ignore[assignment]

# ---- Security / Sessions ----
# Secrets must NOT be committed. In Azure App Service, set this in Configuration.
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "")
if not app.secret_key:
    raise RuntimeError(
        "Missing FLASK_SECRET_KEY. Set it as an environment variable in Azure App Service "
        "(Configuration) or in your local environment before starting."
    )

# Server-side sessions (filesystem). Simple and adequate for a single-instance Web App.
app.config.update(
    SESSION_TYPE="filesystem",
    SESSION_PERMANENT=False,
    SESSION_USE_SIGNER=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("FLASK_COOKIE_SECURE", "true").lower() == "true",
)

session_dir = os.environ.get("FLASK_SESSION_DIR") or os.path.join(os.getcwd(), ".flask_session")
os.makedirs(session_dir, exist_ok=True)
app.config["SESSION_FILE_DIR"] = session_dir
Session(app)

# ---- Authentication ----
# Initializes MSAL/Entra settings from environment and registers auth routes.
init_auth(app)
app.register_blueprint(auth_bp)

@app.context_processor
def inject_user():
    """Make the authenticated user available to all templates as `current_user`."""
    return {"current_user": session.get("user")}

# ----- PATHS -----
# Note: In production, PDFs and vectorstores are served from Azure Blob Storage.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # website_online/

# ----- EMBEDDINGS + LLM -----
@lru_cache(maxsize=1)
def get_embeddings() -> HuggingFaceEmbeddings:
    """
    Lazily construct embeddings.

    IMPORTANT for Azure App Service:
    - SentenceTransformers models download on first load if not cached.
    - Doing this during process startup can exceed the 230s container start timeout.

    We defer initialization to first request and store caches under /home (persistent).
    """

    # Prefer persistent cache on App Service Linux (/home persists across restarts).
    os.environ.setdefault("HF_HOME", "/home/site/wwwroot/.cache/huggingface")
    os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", "/home/site/wwwroot/.cache/sentence_transformers")

    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
    )

@lru_cache(maxsize=1)
def get_llm():
    """
    Lazily construct the Azure OpenAI chat model.

    This keeps app startup more robust during deployments (e.g., if env vars are
    applied slightly after the process starts).
    """
    return get_chat_model()


@lru_cache(maxsize=1)
def get_blob_settings() -> BlobSettings:
    """Load Azure Blob settings from environment (cached)."""
    return BlobSettings.from_env()


@lru_cache(maxsize=1)
def get_blob_client() -> BlobStorageClient:
    """Create Azure Blob client from environment (cached)."""
    return BlobStorageClient.from_env()


@lru_cache(maxsize=1)
def get_vs_manager() -> VectorstoreManager:
    """Create the vectorstore manager (cached)."""
    return VectorstoreManager(
        blob=get_blob_client(),
        settings=get_blob_settings(),
        embeddings=get_embeddings(),
        cache_root=default_cache_dir(),
    )


@lru_cache(maxsize=1)
def get_doc_index():
    """
    Build (and cache) an index of vectorstores by listing blobs.

    Restarting the app refreshes the index.
    """
    s = get_blob_settings()
    b = get_blob_client()
    return build_doc_index_from_blob(b, s.vectorstore_prefix)


def get_categories() -> list[str]:
    return sorted(get_doc_index().keys())

def get_vectorstore(doc_id: str):
    """
    doc_id is like 'ACI_Codes/2019/aci_2019'
    """
    return get_vs_manager().get_vectorstore(doc_id)

def get_doc_info(doc_id: str):
    idx = get_doc_index()
    for cat in idx:
        for year in idx[cat]:
            for d in idx[cat][year]:
                if d["id"] == doc_id:
                    return d
    return None

# ---------- ROUTES ----------

@app.route("/")
@domain_required
def index():
    # Initial page with dropdowns + question form
    return render_template("index.html", categories=get_categories())


@app.route("/years")
@domain_required
def years_for_category():
    category = request.args.get("category")
    idx = get_doc_index()
    if not category or category not in idx:
        return jsonify([])
    years = sorted(idx[category].keys())
    return jsonify(years)


@app.route("/docs")
@domain_required
def docs_for_year():
    """
    AJAX endpoint: /docs?category=ACI_Codes&year=2019
    Returns JSON list of documents for that category and year.
    """
    category = request.args.get("category")
    year = request.args.get("year")
    
    if not category or not year:
         return jsonify([])
         
    docs = get_doc_index().get(category, {}).get(year, [])
    return jsonify(docs)


@app.route("/ask", methods=["POST"])
@domain_required
def ask():
    doc_id = request.form.get("doc_id")
    question = request.form.get("question", "").strip()

    if not doc_id or not question:
        return redirect(url_for("index"))

    doc_info = get_doc_info(doc_id)
    if not doc_info:
        return f"Unknown document id: {doc_id}", 400

    # 1. Load vectorstore and retrieve relevant chunks
    vs = get_vectorstore(doc_id)
    retriever = vs.as_retriever(k=4)
    docs = retriever.invoke(question)

    if not docs:
        answer = "I couldn't find relevant information in this document."
        pages = []
    else:
        # 2. Build context + collect page numbers
        pages_raw = [d.metadata.get("page") for d in docs if "page" in d.metadata]

        # Unique, sorted
        unique_pages_raw = sorted(set(pages_raw))

        # Many loaders store pages as 0-based; convert to human 1-based.
        if unique_pages_raw and min(unique_pages_raw) == 0:
            pages_display = [p + 1 for p in unique_pages_raw]
            first_page_for_viewer = unique_pages_raw[0] + 1
        else:
            pages_display = unique_pages_raw
            first_page_for_viewer = unique_pages_raw[0] if unique_pages_raw else 1

        context = "\n\n".join(d.page_content for d in docs)

        # 3. Ask LLM using RAG prompt
        prompt = f"""
You are an assistant answering questions about engineering / construction codes.

Use ONLY the information in the context below.
If the answer is not clearly contained in the context, say you don't know.

Context:
{context}

Question:
{question}
"""
        llm_response = get_llm().invoke(prompt)
        # LangChain chat models can return either str or a Message; handle both.
        answer = getattr(llm_response, "content", llm_response)

    # 4. Build PDF URL
    pdf_rel_path = doc_info["pdf_rel_path"]
    pdf_url = url_for("serve_pdf", doc_path=pdf_rel_path)

    return render_template(
        "result.html",
        question=question,
        answer=answer,
        pages=pages_display if docs else [],
        pdf_url=pdf_url,
        first_page=first_page_for_viewer if docs else 1,
        doc_label=doc_info["label"],
    )


@app.route("/pdf/<path:doc_path>")
@domain_required
def serve_pdf(doc_path):
    """
    Serve PDF files from Azure Blob Storage.

    The vector creation pipeline uploads PDFs under:
      {AZURE_BLOB_PDF_PREFIX}/{doc_path}

    Example:
      doc_path:  ACI_Codes/2019/ACI 318-19.pdf
      blob:      pdfs/ACI_Codes/2019/ACI 318-19.pdf
    """

    # Basic path safety: prevent traversal.
    norm = doc_path.replace("\\", "/")
    if ".." in norm or norm.startswith("/"):
        return "Invalid PDF path.", 400

    settings = get_blob_settings()
    blob_client = get_blob_client()
    blob_name = f"{settings.pdf_prefix}/{norm}".replace("//", "/")

    if not blob_client.blob_exists(blob_name):
        return f"PDF not found: {doc_path}", 404

    return Response(
        stream_with_context(blob_client.stream_blob(blob_name)),
        mimetype="application/pdf",
        headers={"Cache-Control": "private, max-age=3600"},
    )


@app.route("/ask_stream", methods=["POST"])
@domain_required
def ask_stream():
    data = request.get_json()
    doc_id = data.get("doc_id")
    question = data.get("question", "").strip()

    if not doc_id or not question:
        return jsonify({"error": "Missing doc_id or question"}), 400

    doc_info = get_doc_info(doc_id)
    if not doc_info:
        return jsonify({"error": "Unknown document"}), 400

    # 1. Retrieval
    vs = get_vectorstore(doc_id)
    retriever = vs.as_retriever(k=4)
    docs = retriever.invoke(question)

    # 2. Prepare Metadata
    if not docs:
        # No context found
        def generate_empty():
            yield json.dumps({
                "type": "meta",
                "pages": [],
                "pdf_url": url_for("serve_pdf", doc_path=doc_info["pdf_rel_path"]),
                "first_page": 1,
                "doc_label": doc_info["label"]
            }) + "\n"
            yield json.dumps({
                "type": "token",
                "content": "I couldn't find relevant information in this document."
            }) + "\n"
        return Response(stream_with_context(generate_empty()), mimetype='application/x-ndjson')

    # Process pages
    pages_raw = [d.metadata.get("page") for d in docs if "page" in d.metadata]
    unique_pages_raw = sorted(set(pages_raw))
    
    if unique_pages_raw and min(unique_pages_raw) == 0:
        pages_display = [p + 1 for p in unique_pages_raw]
        first_page_for_viewer = unique_pages_raw[0] + 1
    else:
        pages_display = unique_pages_raw
        first_page_for_viewer = unique_pages_raw[0] if unique_pages_raw else 1

    context = "\n\n".join(d.page_content for d in docs)
    
    prompt = f"""
You are an assistant answering questions about engineering / construction codes.

Use ONLY the information in the context below.
If the answer is not clearly contained in the context, say you don't know.

Context:
{context}

Question:
{question}
"""

    def generate():
        # Yield metadata first
        yield json.dumps({
            "type": "meta",
            "pages": pages_display,
            "pdf_url": url_for("serve_pdf", doc_path=doc_info["pdf_rel_path"]),
            "first_page": first_page_for_viewer,
            "doc_label": doc_info["label"]
        }) + "\n"

        # Stream answer
        for chunk in get_llm().stream(prompt):
            content = getattr(chunk, "content", chunk)
            if content:
                yield json.dumps({
                    "type": "token",
                    "content": content
                }) + "\n"

    return Response(stream_with_context(generate()), mimetype='application/x-ndjson')


@app.route("/domain_expansion")
@domain_required
def domain_expansion():
    return render_template("domain_expansion.html")


if __name__ == "__main__":
    app.run(debug=True, port=5050)
