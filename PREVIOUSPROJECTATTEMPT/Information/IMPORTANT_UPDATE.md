# ⚠️ IMPORTANT UPDATE - Startup Command Configuration

## The Error You Encountered

```
Error: startup-command is not a valid input for Windows web app or with publish-profile auth scheme.
```

## Why This Happened

When using `publish-profile` authentication (which your GitHub Actions uses), you **cannot** specify the startup command in the GitHub Actions workflow. It must be set in the Azure Portal instead.

## ✅ FIXED - Here's What Changed

### 1. Removed `startup-command` from GitHub Actions
The workflow no longer tries to set the startup command (this was causing the error).

### 2. YOU MUST Set Startup Command in Azure Portal

**This is now REQUIRED before deployment will work:**

1. Go to **Azure Portal**
2. Navigate to your **JOGO** App Service
3. Click **Configuration** in the left menu
4. Click **General settings** tab
5. Find **Startup Command** field
6. Enter: `bash startup.sh`
7. Click **Save** at the top
8. Click **Continue** when prompted

**Screenshot guide:**
```
Azure Portal → JOGO → Configuration → General settings
┌─────────────────────────────────────────┐
│ Stack settings                          │
├─────────────────────────────────────────┤
│ Stack: Python                           │
│ Major version: 3.10                     │
├─────────────────────────────────────────┤
│ Startup Command                         │
│ ┌─────────────────────────────────────┐ │
│ │ bash startup.sh                     │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

## Order of Operations

1. ✅ **Push the updated code** (remove startup-command from workflow)
   ```bash
   git add .
   git commit -m "Fix startup command configuration for Azure"
   git push origin main
   ```

2. ⚠️ **BEFORE deployment completes, set startup command in Azure Portal**
   - Azure Portal → JOGO → Configuration → General settings
   - Startup Command: `bash startup.sh`
   - Save

3. ✅ **Then set environment variables** (also in Configuration → Application settings)

4. ✅ **Restart the app** (optional, but recommended)

## Why This Matters

Without the startup command set in Azure Portal:
- ❌ Azure won't know how to start your Flask app
- ❌ Deployment will complete but app will crash
- ❌ You'll see container startup errors

With the startup command properly configured:
- ✅ Azure runs `bash startup.sh`
- ✅ Gunicorn starts correctly
- ✅ App runs on port 8000
- ✅ Everything works!

## Quick Reference

**Startup command to use:** `bash startup.sh`

**Where to set it:** Azure Portal → JOGO → Configuration → General settings → Startup Command

**When to set it:** BEFORE or immediately after pushing your code

---

## Next Steps

See `QUICK_FIX.md` for the complete updated checklist with the correct order of operations.

---

**The deployment will work now - just remember to set the startup command in Azure Portal! 🚀**

