import os
import json
import requests
from flask import Flask, render_template, request, Response, stream_with_context
from identity.flask import Auth
import app_config

# Import our new services
from storage.blob_service import BlobService
from rag.search_service import SearchService

__version__ = "0.9.0"

app = Flask(__name__)
app.config.from_object(app_config)
auth = Auth(
    app,
    authority=os.getenv("AUTHORITY"),
    client_id=os.getenv("CLIENT_ID"),
    client_credential=os.getenv("CLIENT_SECRET"),
    redirect_uri=os.getenv("REDIRECT_URI"),
    oidc_authority=os.getenv("OIDC_AUTHORITY"),
    b2c_tenant_name=os.getenv('B2C_TENANT_NAME'),
    b2c_signup_signin_user_flow=os.getenv('SIGNUPSIGNIN_USER_FLOW'),
    b2c_edit_profile_user_flow=os.getenv('EDITPROFILE_USER_FLOW'),
    b2c_reset_password_user_flow=os.getenv('RESETPASSWORD_USER_FLOW'),
)

# Initialize Services
# Note: We initialize them globally or per request. 
# Global is better for connection pooling, but BlobService is lightweight.
blob_service = BlobService()
search_service = SearchService()

@app.route("/")
def index(*, context=None):
    # 1. Fetch Hierarchy for Dropdowns
    hierarchy = blob_service.list_blobs_hierarchy()
    
    # 2. Mock User (as requested)
    mock_context = {
        'user': {'name': 'Test User', 'preferred_username': 'test@example.com'}
    }
    
    return render_template(
        'index.html',
        user=mock_context['user'],
        edit_profile_url="#",
        api_endpoint=os.getenv("ENDPOINT"),
        title=f"Flask Web App Sample v{__version__}",
        hierarchy=hierarchy # Pass data to template
    )


'''
@auth.login_required
def index(*, context):
    return render_template(
        'index.html',
        user=context['user'],
        edit_profile_url=auth.get_edit_profile_url(),
        api_endpoint=os.getenv("ENDPOINT"),
        title=f"Flask Web App Sample v{__version__}",
    )
'''



@app.route("/ask_stream", methods=["POST"])
def ask_stream():
    data = request.get_json()
    doc_id = data.get('doc_id')
    question = data.get('question')
    
    if not doc_id or not question:
        return Response("Missing doc_id or question", status=400)

    def generate():
        # 1. Perform Search
        results = search_service.search(doc_id, question)
        
        if not results:
            yield json.dumps({'type': 'token', 'content': 'No relevant information found.'}) + '\n'
            return

        # 2. Extract Metadata
        # Unique pages found
        pages = sorted(list(set(r['page'] for r in results)))
        # PDF URL
        pdf_url = search_service.get_document_url(doc_id)
        
        # 3. Send Metadata First
        meta_payload = {
            'type': 'meta',
            'pages': pages,
            'pdf_url': pdf_url,
            'doc_label': doc_id.split('/')[-1] # Simple label
        }
        yield json.dumps(meta_payload) + '\n'

        # 4. Stream Content (Simulated as chunks for the frontend chat)
        yield json.dumps({'type': 'token', 'content': f"Found {len(results)} relevant snippets:\n\n"}) + '\n'
        
        for i, res in enumerate(results):
            # Format: **Page X**: Content...
            snippet_text = f"**Page {res['page']}**:\n{res['content']}\n\n"
            
            # Simulate streaming token by token or line by line
            # For simplicity, we yield the whole snippet as one "token" event
            yield json.dumps({'type': 'token', 'content': snippet_text}) + '\n'

    return Response(stream_with_context(generate()), content_type='application/x-ndjson')


# --- Existing Routes ---

@app.route("/call_api")
@auth.login_required(scopes=os.getenv("SCOPE", "").split())
def call_downstream_api(*, context):
    api_result = requests.get(
        os.getenv("ENDPOINT"),
        headers={'Authorization': 'Bearer ' + context['access_token']},
        timeout=30,
    ).json() if context.get('access_token') else "Did you forget to set the SCOPE environment variable?"
    return render_template('display.html', title="API Response", result=api_result)


@app.route("/result", methods=["POST"])
def result():
    question = request.form.get("question")
    doc_label = request.form.get("doc_label")
    pages = request.form.get("pages")
    pdf_url = request.form.get("pdf_url")
    return render_template('result.html', question=question, doc_label=doc_label, pages=pages, pdf_url=pdf_url)

@app.route("/domain_expansion")
def domain_expansion():
    return render_template('domain_expansion.html')
