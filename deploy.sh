#!/bin/bash

echo "🚀 Model Verse Chain Deployment Script"
echo "======================================"

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "❌ Git repository not found. Please initialize git first:"
    echo "   git init"
    echo "   git add ."
    echo "   git commit -m 'Initial commit'"
    echo "   git remote add origin <your-github-repo-url>"
    echo "   git push -u origin main"
    exit 1
fi

# Check if we have uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️  You have uncommitted changes. Please commit them first:"
    echo "   git add ."
    echo "   git commit -m 'Deployment preparation'"
    echo "   git push"
    exit 1
fi

echo "✅ Git repository is clean"

# Check if environment variables are set
if [ -z "$OPENROUTER_API_KEYS" ]; then
    echo "⚠️  OPENROUTER_API_KEYS environment variable not set"
    echo "   Please set your OpenRouter API keys before deploying"
    echo "   export OPENROUTER_API_KEYS='your-api-key-1,your-api-key-2'"
fi

echo ""
echo "📋 Deployment Options:"
echo "1. Railway (Recommended - Easiest)"
echo "2. Render (Good Alternative)"
echo "3. Vercel + Railway (Most Professional)"
echo ""
echo "Please choose your deployment platform and follow the instructions in DEPLOYMENT.md"
echo ""
echo "🔗 Quick Links:"
echo "- Railway: https://railway.app"
echo "- Render: https://render.com"
echo "- Vercel: https://vercel.com"
echo ""
echo "📖 Full deployment guide: DEPLOYMENT.md" 