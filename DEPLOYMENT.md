# Deployment Guide for Model Verse Chain

This guide provides multiple deployment options for your AI chat application.

## 🚀 Quick Deploy Options

### Option 1: Railway (Recommended - Easiest)

**Railway** is the easiest option as it can deploy both frontend and backend together.

#### Steps:
1. **Push to GitHub**: Ensure your code is in a GitHub repository
2. **Connect Railway**: 
   - Go to [railway.app](https://railway.app)
   - Sign up with GitHub
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository
3. **Configure Environment Variables**:
   - Go to your project settings
   - Add these environment variables:
     ```
     OPENROUTER_API_KEYS=your-api-key-1,your-api-key-2
     ALLOWED_ORIGINS=https://your-app.railway.app,http://localhost:3000
     ```
4. **Deploy**: Railway will automatically build and deploy your app
5. **Get URL**: Your app will be available at `https://your-app.railway.app`

### Option 2: Render (Good Alternative)

**Render** offers free hosting for both services.

#### Steps:
1. **Push to GitHub**: Ensure your code is in a GitHub repository
2. **Deploy Backend**:
   - Go to [render.com](https://render.com)
   - Create account and connect GitHub
   - Click "New" → "Web Service"
   - Connect your repository
   - Configure:
     - **Name**: `model-verse-backend`
     - **Environment**: `Python 3`
     - **Build Command**: `cd backend && pip install -r requirements.txt`
     - **Start Command**: `cd backend && python main.py`
   - Add environment variables:
     ```
     OPENROUTER_API_KEYS=your-api-key-1,your-api-key-2
     ALLOWED_ORIGINS=https://your-frontend-url.onrender.com
     ```

3. **Deploy Frontend**:
   - Click "New" → "Static Site"
   - Connect your repository
   - Configure:
     - **Name**: `model-verse-frontend`
     - **Build Command**: `npm install && npm run build`
     - **Publish Directory**: `dist`
   - Add environment variable:
     ```
     VITE_API_BASE_URL=https://your-backend-url.onrender.com
     ```

### Option 3: Vercel + Railway (Most Professional)

Deploy frontend on Vercel and backend on Railway for best performance.

#### Steps:
1. **Deploy Backend on Railway** (follow Option 1 steps)
2. **Deploy Frontend on Vercel**:
   - Go to [vercel.com](https://vercel.com)
   - Sign up with GitHub
   - Import your repository
   - Configure environment variable:
     ```
     VITE_API_BASE_URL=https://your-backend-url.railway.app
     ```
   - Deploy

## 🔧 Environment Variables

### Backend Variables
```bash
OPENROUTER_API_KEYS=your-api-key-1,your-api-key-2,your-api-key-3
ALLOWED_ORIGINS=https://your-frontend-domain.com,http://localhost:3000
```

### Frontend Variables
```bash
VITE_API_BASE_URL=https://your-backend-domain.com
```

## 📋 Pre-deployment Checklist

- [ ] Code is pushed to GitHub
- [ ] API keys are ready (get from [OpenRouter](https://openrouter.ai/))
- [ ] All dependencies are in `requirements.txt` and `package.json`
- [ ] Environment variables are configured
- [ ] CORS origins are set correctly

## 🐛 Troubleshooting

### Common Issues:

1. **CORS Errors**:
   - Ensure `ALLOWED_ORIGINS` includes your frontend URL
   - Check that URLs don't have trailing slashes

2. **API Key Errors**:
   - Verify your OpenRouter API keys are valid
   - Check API key format (should start with `sk-or-v1-`)

3. **Build Failures**:
   - Check that all dependencies are listed
   - Verify Python version compatibility

4. **Port Issues**:
   - Railway/Render will set their own PORT environment variable
   - The backend code handles this automatically

### Health Check:
Your backend includes a health check endpoint at `/health`. Use this to verify deployment:
```
https://your-backend-url.com/health
```

## 🔒 Security Notes

1. **Never commit API keys** to your repository
2. **Use environment variables** for all sensitive data
3. **Set up proper CORS** to prevent unauthorized access
4. **Consider rate limiting** for production use

## 📊 Monitoring

After deployment:
1. Check the health endpoint regularly
2. Monitor API usage and costs
3. Set up logging if needed
4. Consider adding error tracking (Sentry, etc.)

## 🚀 Next Steps

Once deployed:
1. Test all features thoroughly
2. Set up a custom domain (optional)
3. Configure SSL certificates (automatic on most platforms)
4. Set up monitoring and alerts
5. Consider adding a CDN for better performance

## 📞 Support

If you encounter issues:
1. Check the platform's documentation
2. Review the troubleshooting section
3. Check the application logs
4. Verify environment variables are set correctly 