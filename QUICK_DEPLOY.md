# 🚀 Quick Deployment Guide

## **RECOMMENDED: Railway (Easiest)**

### Step 1: Prepare Your Code
```bash
# Make sure all changes are committed
git add .
git commit -m "Prepare for deployment"
git push
```

### Step 2: Deploy on Railway
1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your repository
5. Add environment variables:
   ```
   OPENROUTER_API_KEYS=your-api-key-1,your-api-key-2
   ALLOWED_ORIGINS=https://your-app.railway.app,http://localhost:3000
   ```
6. Deploy! 🎉

### Step 3: Get Your URL
Your app will be available at: `https://your-app-name.railway.app`

---

## **Alternative: Render**

### Backend Deployment:
1. Go to [render.com](https://render.com)
2. Create account → "New Web Service"
3. Connect your GitHub repo
4. Configure:
   - **Build Command**: `cd backend && pip install -r requirements.txt`
   - **Start Command**: `cd backend && python main.py`
5. Add environment variables (same as Railway)

### Frontend Deployment:
1. "New Static Site" on Render
2. Same repo, configure:
   - **Build Command**: `npm install && npm run build`
   - **Publish Directory**: `dist`
   - **Environment Variable**: `VITE_API_BASE_URL=https://your-backend-url.onrender.com`

---

## **What I Fixed for You:**

✅ **Fixed linter error** in `backend/main.py` (filename null check)  
✅ **Made API keys configurable** via environment variables  
✅ **Updated CORS** to work with deployment URLs  
✅ **Created deployment configs** for Railway, Render, Vercel  
✅ **Added environment variable support** for frontend  
✅ **Created comprehensive guides** and scripts  

---

## **Before You Deploy:**

1. **Get OpenRouter API keys** from [openrouter.ai](https://openrouter.ai/)
2. **Test locally** first:
   ```bash
   cd backend && python main.py
   # In another terminal:
   npm run dev
   ```
3. **Run the deployment script**:
   ```bash
   # Windows:
   deploy.bat
   
   # Linux/Mac:
   ./deploy.sh
   ```

---

## **Need Help?**

- 📖 Full guide: `DEPLOYMENT.md`
- 🔧 Troubleshooting: Check the troubleshooting section in `DEPLOYMENT.md`
- 🆘 Health check: `https://your-backend-url.com/health`

**Your app is now ready for deployment! 🎉** 