# Azure Deployment Fix Summary

## Problem
Your Flask application was building successfully but crashing during deployment on Azure App Service. The error indicated that the deployment was starting but Azure didn't know how to run your application.

## Root Causes
1. **Missing startup command**: Azure didn't know how to start your Flask app
2. **No WSGI server configuration**: Gunicorn wasn't being invoked properly
3. **Missing deployment configuration**: Azure needed explicit instructions

## Changes Made

### 1. Created `startup.sh`
A startup script that:
- Creates necessary cache directories for HuggingFace models
- Sets environment variables for caching
- Starts Gunicorn with proper configuration (port 8000, 4 workers, 600s timeout)

### 2. Updated `.github/workflows/main_jogo.yml`
Added to the deployment step:
```yaml
package: '.'
startup-command: 'bash startup.sh'
```

### 3. Created `.deployment`
Azure-specific configuration file that ensures build happens during deployment.

### 4. Created `AZURE_SETUP.md`
Complete documentation of all required environment variables and Azure Portal configuration.

## Next Steps - REQUIRED

### Step 1: Commit and Push Changes
```bash
git add .
git commit -m "Fix Azure deployment with startup script and configuration"
git push origin main
```

### Step 2: Set Startup Command in Azure Portal (CRITICAL!)
Navigate to Azure Portal → Your App Service (JOGO) → Configuration → General settings

**Set Startup Command to:** `bash startup.sh`

Click **Save** at the top, then click **Continue** when prompted.

**Why?** When using `publish-profile` authentication, the startup command cannot be set in GitHub Actions. It must be configured in the Azure Portal.

### Step 3: Configure Azure Portal Environment Variables
Navigate to Azure Portal → Your App Service (JOGO) → Configuration → Application settings

**CRITICAL - You MUST add these environment variables:**

#### Minimum Required (app will crash without these):
- `FLASK_SECRET_KEY`: Generate with `python -c "import secrets; print(secrets.token_hex(32))"`
- `ENTRA_CLIENT_ID`: Your Azure AD app client ID
- `ENTRA_CLIENT_SECRET`: Your Azure AD app client secret  
- `ENTRA_TENANT_ID`: Your Azure AD tenant ID
- `ENTRA_AUTHORITY`: `https://login.microsoftonline.com/{YOUR_TENANT_ID}`
- `ENTRA_REDIRECT_PATH`: `/auth/redirect`
- `ALLOWED_DOMAINS`: Your allowed email domains (comma-separated)
- `AZURE_STORAGE_CONNECTION_STRING`: Your storage account connection string
- `AZURE_BLOB_CONTAINER_NAME`: Your blob container name
- `AZURE_BLOB_PDF_PREFIX`: `pdfs` (or your prefix)
- `AZURE_BLOB_VECTORSTORE_PREFIX`: `vectorstores` (or your prefix)
- `AZURE_OPENAI_API_KEY`: Your OpenAI key
- `AZURE_OPENAI_ENDPOINT`: Your OpenAI endpoint
- `AZURE_OPENAI_API_VERSION`: `2024-02-15-preview` (or your version)
- `AZURE_OPENAI_DEPLOYMENT_NAME`: Your model deployment name

See `AZURE_SETUP.md` for complete details on each variable.

### Step 4: Restart App Service (Optional)
After adding environment variables:
- Azure Portal → Your App Service → Overview → Restart

### Step 5: Monitor Deployment
Watch the GitHub Actions workflow:
- Go to your GitHub repository → Actions tab
- Watch the "Build and deploy Python app to Azure Web App - JOGO" workflow
- Should now complete successfully

### Step 6: Verify Application
After successful deployment:
1. Visit your app URL: `https://jogo.azurewebsites.net` (or your domain)
2. Test authentication flow
3. Try a query (first one may be slow due to model download)

## Troubleshooting

### If deployment still fails:
1. Check GitHub Actions logs for the full error
2. Check Azure Portal → Log Stream for runtime errors
3. Verify all environment variables are set correctly
4. Ensure your App Service plan has sufficient resources (B2 or higher recommended)

### Common Issues After This Fix:
- **Missing environment variables**: Check Azure Portal configuration
- **First request timeout**: Models download on first use, can take 2-3 minutes
- **Memory errors**: Upgrade to B3 or S2 App Service plan

### View Logs in Real-Time:
```bash
# Using Azure CLI
az webapp log tail --name JOGO --resource-group <your-resource-group>
```

Or in Azure Portal → Your App Service → Log Stream

## Why This Fixes the Issue

1. **Explicit startup command**: Azure now knows to run `bash startup.sh`
2. **Proper Gunicorn configuration**: App binds to correct port (8000) with appropriate timeouts
3. **Directory creation**: Cache directories created before app starts
4. **Environment setup**: HuggingFace cache paths set correctly

## Additional Notes

- The startup script has a 600-second timeout to handle large model downloads
- Cache directories persist across restarts at `/home/site/wwwroot/.cache/`
- Gunicorn uses 4 workers (adjust in `startup.sh` if needed)
- All logs go to stdout/stderr for Azure monitoring

## Files Changed
- ✅ `.github/workflows/main_jogo.yml` - Added startup command
- ✅ `startup.sh` - New startup script
- ✅ `.deployment` - New Azure config file
- ✅ `AZURE_SETUP.md` - New documentation
- ✅ `DEPLOYMENT_FIX.md` - This file

