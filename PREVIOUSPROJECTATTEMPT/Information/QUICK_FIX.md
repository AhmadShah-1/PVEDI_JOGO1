# Quick Fix Checklist ✅

## What Was Wrong
❌ Azure didn't know how to start your Flask app → deployment crashed

## What Was Fixed
✅ Created `startup.sh` with Gunicorn configuration  
✅ Updated GitHub Actions workflow with startup command  
✅ Created Azure deployment configuration  

## What You Need to Do NOW

### 1️⃣ Push Changes (2 minutes)
```bash
git add .
git commit -m "Fix Azure deployment with startup script"
git push origin main
```

### 2️⃣ Configure Startup Command in Azure Portal (1 minute)
**Azure Portal → JOGO → Configuration → General Settings → Startup Command**

Set to: `bash startup.sh`

Click **Save** at the top.

### 3️⃣ Set Environment Variables in Azure Portal (5 minutes)
**Azure Portal → JOGO → Configuration → Application Settings → New application setting**

**CRITICAL - Add these (app will crash without them):**
```
FLASK_SECRET_KEY = <generate-with-python-secrets>
ENTRA_CLIENT_ID = <your-azure-ad-client-id>
ENTRA_CLIENT_SECRET = <your-azure-ad-client-secret>
ENTRA_TENANT_ID = <your-azure-ad-tenant-id>
ENTRA_AUTHORITY = https://login.microsoftonline.com/<tenant-id>
ENTRA_REDIRECT_PATH = /auth/redirect
ALLOWED_DOMAINS = <your-domain.com>
AZURE_STORAGE_CONNECTION_STRING = <your-connection-string>
AZURE_BLOB_CONTAINER_NAME = <container-name>
AZURE_BLOB_PDF_PREFIX = pdfs
AZURE_BLOB_VECTORSTORE_PREFIX = vectorstores
AZURE_OPENAI_API_KEY = <your-key>
AZURE_OPENAI_ENDPOINT = <your-endpoint>
AZURE_OPENAI_API_VERSION = 2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT_NAME = <deployment-name>
```

**Generate Flask secret key:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 4️⃣ Watch Deployment (2 minutes)
- GitHub → Actions tab → Watch workflow run
- Should complete successfully now ✅

### 5️⃣ Test App (1 minute)
Visit: `https://jogo.azurewebsites.net`

---

## That's It! 🎉

**Time to fix: ~10 minutes**

See `DEPLOYMENT_FIX.md` for detailed explanation  
See `AZURE_SETUP.md` for complete configuration reference

---

## Still Having Issues?

1. Check GitHub Actions logs
2. Check Azure Portal → Log Stream
3. Verify ALL environment variables are set
4. Make sure App Service plan is B2 or higher

---

**The deployment will work after you complete steps 1️⃣ and 2️⃣ above!**

