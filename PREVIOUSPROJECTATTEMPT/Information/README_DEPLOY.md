## Deploy `website_online` to Azure App Service (Web App)

This Flask app uses:
- **Microsoft Entra ID (MSAL)** for authentication (Authorization Code Flow)
- **Azure Blob Storage** for PDFs and FAISS vectorstores
- **Azure OpenAI** for chat completions

### 1) Create the Azure resources

- **Azure Storage Account**: already created in your setup (e.g. `jogostorage`)
  - Container: `nyccodesvectorstore`
  - Expected prefixes inside the container:
    - `pdfs/...` (original PDFs)
    - `vectorstores_RecursiveSplitting/...` (FAISS artifacts: `index.faiss`, `index.pkl`, `manifest.json`)

- **Azure OpenAI**
  - Create a **chat model deployment** (e.g. `gpt-4o-mini`, `gpt-4.1-mini`, etc.)

- **Azure App Service (Web App)** (Linux recommended)
  - Runtime: Python 3.10+ (3.11 recommended)

### 2) App Registration (Entra ID) for MSAL

In Azure Portal:
- Microsoft Entra ID → **App registrations** → **New registration**
- Supported account types: usually **Single tenant** (typical for a company-only app)
- Redirect URI:
  - Type: Web
  - Value: `https://<YOUR-WEBAPP-NAME>.azurewebsites.net/auth/callback`

Then:
- **Certificates & secrets** → create a **Client secret**
- **Overview** → note:
  - Application (client) ID
  - Directory (tenant) ID

### 3) Configure Web App environment variables

Azure Portal → Web App → **Configuration** → **Application settings**:

#### Flask / session
- `FLASK_SECRET_KEY`: strong random string
- `FLASK_COOKIE_SECURE`: `true` (recommended for production)
- `FLASK_SESSION_DIR`: optional; defaults to `.flask_session` under the app working directory

#### Entra ID / MSAL
- `AAD_TENANT_ID`: your tenant ID
- `AAD_CLIENT_ID`: your app registration client ID
- `AAD_CLIENT_SECRET`: the client secret value
- `AAD_ALLOWED_EMAIL_DOMAIN`: `pvedi-ae.com`
- `AAD_SCOPES`: `openid profile email` (default)

#### Azure Blob Storage
- `AZURE_STORAGE_CONNECTION_STRING`: from Storage Account → Access keys
- `AZURE_BLOB_CONTAINER`: `nyccodesvectorstore`
- `AZURE_BLOB_PDF_PREFIX`: `pdfs`
- `AZURE_BLOB_VECTORSTORE_PREFIX`: `vectorstores_RecursiveSplitting`

#### Azure OpenAI
- `AZURE_OPENAI_ENDPOINT`: like `https://<name>.openai.azure.com/`
- `AZURE_OPENAI_API_KEY`: your key
- `AZURE_OPENAI_API_VERSION`: e.g. `2024-06-01`
- `AZURE_OPENAI_DEPLOYMENT`: your deployment name

#### Optional: vectorstore cache directory
- `RAG_CACHE_DIR`: (Linux) `/tmp/rag_cache` is a good default

### 4) Deploy code

Any of these approaches work:
- **GitHub Actions** (recommended)
- **ZIP deploy**
- **Azure CLI** deploy

Make sure the deployed folder includes:
- `app.py`
- `templates/`
- `static/`
- `auth/`, `storage/`, `rag/`, `llm/`
- `requirements.txt`

### 5) Startup command

Azure Portal → Web App → **Configuration** → **General settings** → Startup command:

```bash
gunicorn -w 2 -b 0.0.0.0:8000 app:app
```

### 6) Verify

- Open `https://<YOUR-WEBAPP>.azurewebsites.net/`
- You should be redirected to Microsoft login
- Only `@pvedi-ae.com` accounts will be allowed

### Notes / Operational guidance

- **Sessions**: filesystem sessions are simplest but assume a single instance or sticky sessions. If you later scale out, switch to Redis-backed sessions.
- **FAISS safety**: we use `allow_dangerous_deserialization=True` when loading FAISS metadata because `index.pkl` is a pickle. Only do this when you fully control the Blob container content (you do).
- **PDF streaming**: PDFs are streamed from Blob; for very large PDFs, performance depends on your region and App Service tier.


