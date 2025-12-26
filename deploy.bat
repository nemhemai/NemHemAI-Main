@echo off
echo 🚀 Model Verse Chain Deployment Script
echo ======================================

REM Check if git is initialized
if not exist ".git" (
    echo ❌ Git repository not found. Please initialize git first:
    echo    git init
    echo    git add .
    echo    git commit -m "Initial commit"
    echo    git remote add origin ^<your-github-repo-url^>
    echo    git push -u origin main
    pause
    exit /b 1
)

REM Check if we have uncommitted changes
git diff-index --quiet HEAD
if errorlevel 1 (
    echo ⚠️  You have uncommitted changes. Please commit them first:
    echo    git add .
    echo    git commit -m "Deployment preparation"
    echo    git push
    pause
    exit /b 1
)

echo ✅ Git repository is clean

REM Check if environment variables are set
if "%OPENROUTER_API_KEYS%"=="" (
    echo ⚠️  OPENROUTER_API_KEYS environment variable not set
    echo    Please set your OpenRouter API keys before deploying
    echo    set OPENROUTER_API_KEYS=your-api-key-1,your-api-key-2
)

echo.
echo 📋 Deployment Options:
echo 1. Railway (Recommended - Easiest)
echo 2. Render (Good Alternative)
echo 3. Vercel + Railway (Most Professional)
echo.
echo Please choose your deployment platform and follow the instructions in DEPLOYMENT.md
echo.
echo 🔗 Quick Links:
echo - Railway: https://railway.app
echo - Render: https://render.com
echo - Vercel: https://vercel.com
echo.
echo 📖 Full deployment guide: DEPLOYMENT.md
pause 