# Azure App Service Configuration Guide

## Required Environment Variables in Azure Portal

Navigate to your Azure App Service → Configuration → Application settings and add the following:

### Flask Configuration
- `FLASK_SECRET_KEY`: A secure random string (generate with `python -c "import secrets; print(secrets.token_hex(32))"`)
- `FLASK_COOKIE_SECURE`: `true` (for production HTTPS)
- `FLASK_SESSION_DIR`: `/home/site/wwwroot/.flask_session` (optional, defaults to this)

### Microsoft Entra ID (Authentication)
- `ENTRA_CLIENT_ID`: Your Azure AD app registration client ID
- `ENTRA_CLIENT_SECRET`: Your Azure AD app registration client secret
- `ENTRA_TENANT_ID`: Your Azure AD tenant ID
- `ENTRA_AUTHORITY`: `https://login.microsoftonline.com/{TENANT_ID}`
- `ENTRA_REDIRECT_PATH`: `/auth/redirect` (or your custom path)
- `ALLOWED_DOMAINS`: Comma-separated list of allowed email domains (e.g., `example.com,company.com`)

### Azure Blob Storage
- `AZURE_STORAGE_CONNECTION_STRING`: Your Azure Storage account connection string
- `AZURE_BLOB_CONTAINER_NAME`: The container name for your blobs (e.g., `documents`)
- `AZURE_BLOB_PDF_PREFIX`: Prefix path for PDFs in blob storage (e.g., `pdfs`)
- `AZURE_BLOB_VECTORSTORE_PREFIX`: Prefix path for vectorstores (e.g., `vectorstores`)

### Azure OpenAI
- `AZURE_OPENAI_API_KEY`: Your Azure OpenAI API key
- `AZURE_OPENAI_ENDPOINT`: Your Azure OpenAI endpoint URL
- `AZURE_OPENAI_API_VERSION`: API version (e.g., `2024-02-15-preview`)
- `AZURE_OPENAI_DEPLOYMENT_NAME`: Your deployment name (e.g., `gpt-4`)

### App Service Configuration
- `SCM_DO_BUILD_DURING_DEPLOYMENT`: `true` (already set by default)
- `WEBSITE_HTTPLOGGING_RETENTION_DAYS`: `7` (optional, for debugging)

## Startup Command

The startup command is now specified in the GitHub Actions workflow and uses `startup.sh`:

```bash
bash startup.sh
```

This starts Gunicorn with appropriate settings for Azure App Service.

## Build Configuration

The app uses Oryx build during deployment, which:
1. Detects Python from `requirements.txt`
2. Installs dependencies using `pip install -r requirements.txt`
3. Starts the app using the startup command

## Port Configuration

Azure App Service automatically routes traffic to port 8000, which is what Gunicorn binds to in `startup.sh`.

## Deployment Troubleshooting

### If deployment still fails:

1. **Check deployment logs** in Azure Portal → Deployment Center → Logs
2. **Check application logs** in Azure Portal → Log stream
3. **Verify environment variables** are all set correctly
4. **Check startup timeout**: Large models may take time to load. The startup timeout is set to 600s in `startup.sh`

### Common Issues:

- **Missing environment variables**: Ensure all required env vars are set
- **Model download timeout**: First deployment may be slow due to HuggingFace model downloads
- **Memory issues**: Ensure your App Service plan has sufficient memory (B2 or higher recommended)

## Testing Locally

To test the startup script locally:

```bash
# Set environment variables
export FLASK_SECRET_KEY="your-secret-key"
# ... set other env vars ...

# Make startup script executable
chmod +x startup.sh

# Run startup script
./startup.sh
```

## Recommended App Service Plan

For this application with ML models:
- **Minimum**: B2 (2 cores, 3.5 GB RAM)
- **Recommended**: B3 or S2 (4 cores, 7 GB RAM)
- **Production**: P1V2 or higher (auto-scaling support)

## Post-Deployment Verification

After deployment succeeds:
1. Visit your app URL
2. Check if authentication redirects work
3. Test a query to ensure models load correctly
4. Monitor initial load time (models download on first request)

