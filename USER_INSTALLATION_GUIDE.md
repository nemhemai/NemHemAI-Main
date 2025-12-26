# 🤖 NemhemAI - User Installation Guide

**Welcome to NemhemAI!** Your personal AI assistant that runs entirely on your computer.

---

## ⚡ Quick Start (3 Steps)

### 1️⃣ Install Ollama
Download from: **https://ollama.com/download**

Then run:
```powershell
ollama pull llama3
```

### 2️⃣ Install NemhemAI
Double-click: **`NemhemAI-Setup-v1.0.0.exe`**

### 3️⃣ Launch & Enjoy!
Click the desktop shortcut and start chatting! 🎉

---

## 📋 System Requirements

| Requirement | Details |
|------------|---------|
| **OS** | Windows 10 or 11 (64-bit) |
| **RAM** | 4 GB minimum, 8 GB recommended |
| **Storage** | 3 GB free space |
| **Internet** | One-time download of AI models |

**You do NOT need:**
- ❌ Python
- ❌ Node.js  
- ❌ Any programming knowledge

---

## 🚀 Detailed Installation

### Step 1: Install Ollama (Required)

Ollama runs the AI models locally on your computer.

#### 1.1 Download Ollama
1. Visit: **https://ollama.com/download**
2. Click **"Download for Windows"**
3. Run the installer

#### 1.2 Download AI Model
Open **PowerShell** or **Command Prompt**:

```powershell
ollama pull llama3
```

⏱️ **Time:** 5-15 minutes (downloads ~4 GB)

#### 1.3 Verify It Works
Open browser → **http://localhost:11434**  
Should show: **"Ollama is running"** ✅

---

### Step 2: Install NemhemAI

#### 2.1 Run the Installer
Double-click: **`NemhemAI-Setup-v1.0.0.exe`**

**Windows Security Warning?**
- Click **"More info"** → **"Run anyway"**
- This is normal for apps without code signing

#### 2.2 Installation Wizard

1. **Welcome** → Click **"Next"**
2. **Ollama Check** → Installer verifies Ollama is installed
3. **Location** → Choose install folder (default: `C:\Program Files\NemhemAI\`)
4. **Shortcuts** → ☑️ Desktop ☑️ Start Menu
5. **Install** → Click **"Install"** and wait 1-2 minutes
6. **Finish** → Click **"Finish"**

✅ **Installation complete!**

---

## 🎯 How to Use NemhemAI

### Launching the App

**Option 1:** Double-click **NemhemAI** icon on desktop  
**Option 2:** Start Menu → Search "NemhemAI" → Click

### First Time Setup

1. **Sign Up**
   - Choose username
   - Create password
   - Click "Create Account"

2. **Login**
   - Enter your credentials
   - Click "Login"

3. **Start Chatting!**
   - Type your question
   - Press Enter
   - Wait for AI response (5-30 seconds)

### What You'll See

- **Desktop Window:** NemhemAI opens in its own window (not browser)
- **Console Window:** A black window in the background (keep it open!)

---

## 💬 Features

### Chat with AI
Ask anything:
- "Explain quantum physics simply"
- "Write a Python function to sort a list"
- "Give me 5 healthy dinner ideas"
- "Help me write a professional email"

### Upload Files
Supported formats:
- **Documents:** PDF, DOCX
- **Images:** JPG, PNG, GIF
- **Data:** CSV files

**Example:**
1. Click 📎 attachment icon
2. Select your PDF
3. Ask: "Summarize this document"

### Data Analysis
Upload CSV files for automatic:
- ✅ Statistical analysis
- ✅ Charts and graphs
- ✅ AI-powered insights

### Switch AI Models
Choose different models:
- **Llama 2:** General purpose (default)
- **Llama 3:** Better responses
- **Mistral:** Faster, smaller
- **DeepSeek - V2** For coding help

---

## 🐛 Troubleshooting

### Problem: "Ollama not found"

**Solution:**
```powershell
# Check if Ollama is running
ollama list

# Start Ollama if needed
ollama serve
```

---

### Problem: AI not responding

**Solution:**
```powershell
# Download the model
ollama pull llama3

# Test it works
ollama run llama3 "Hello"
```

---

### Problem: App won't start

**Solutions:**
1. Check Ollama is running (system tray icon)
2. Run as Administrator
3. Restart computer
4. Check console window for errors

---

### Problem: Slow responses

**Causes & Fixes:**
- **First response always slower** → Normal
- **Low RAM (< 4 GB)** → Close other apps
- **Large conversation** → Start new chat
- **CPU at 100%** → Normal during AI generation

---

### Problem: Windows security warning

**"Windows protected your PC"**

**Solution:**
1. Click **"More info"**
2. Click **"Run anyway"**
3. This is safe - app runs locally on your PC

---

## ⚙️ Configuration

### Where is My Data?

Everything stored locally:
```
C:\Program Files\NemhemAI\
└── backend\
    ├── users.db       ← Your account
    ├── databases\     ← Analysis data
    └── uploads\       ← Your files
```

### Change AI Model

Download more models:
```powershell
ollama pull llama3     # Newer, better
ollama pull mistral     # Faster, smaller
ollama pull deepseek-v2@latest  # For coding
```

Then select in app dropdown menu.

---

## 🔄 Updating

### When New Version Released

1. **Backup data** (optional):
   - Copy `C:\Program Files\NemhemAI\backend\users.db`

2. **Uninstall old version**:
   - Windows Settings → Apps → NemhemAI → Uninstall

3. **Install new version**:
   - Run new installer

4. **Restore data**:
   - Copy back `users.db` file

---

## 🗑️ Uninstalling

### Remove NemhemAI

1. Windows Settings (Win + I)
2. Apps → Installed apps
3. Find **NemhemAI**
4. Click **⋮** → **Uninstall**

### Remove Ollama (Optional)

Only if you don't need it anymore:
1. Windows Settings → Apps
2. Find **Ollama**
3. Uninstall

---

## 🔐 Privacy

### Your Data is Private

✅ **Everything runs locally** on your computer  
✅ **No cloud servers** - no data sent anywhere  
✅ **No tracking** or telemetry  
✅ **Your files stay on your PC**  

### What NemhemAI Accesses

- ✅ Files you explicitly upload
- ✅ Ollama API (localhost only)
- ❌ Internet (except Ollama)
- ❌ Your other files
- ❌ Your personal data

---

## 💡 Tips for Best Results

### Writing Good Prompts

❌ **Vague:** "Tell me about history"  
✅ **Specific:** "Explain causes of WWI in 200 words"

❌ **Too broad:** "Help with code"  
✅ **Detailed:** "Write Python function to read CSV and plot graph"

### Using Models

| Task | Best Model |
|------|-----------|
| General chat | Llama 2/3 |
| Fast answers | Mistral |
| Coding help | Deepseek-v2 |
| Complex reasoning | Llama 3 |

### Performance Tips

1. ✅ Close unused apps
2. ✅ Use Mistral for speed
3. ✅ Start new chat for new topics
4. ✅ Restart app if sluggish

---

## 📞 Support

### Need Help?

1. **Check console window** (black window) for errors
2. **Check Ollama status**: http://localhost:11434
3. **View logs** in console window

### Common Commands

```powershell
# List installed models
ollama list

# Test Ollama
ollama run llama3 "Say hello"

# Restart Ollama
ollama serve
```

### Contact Support

- **GitHub:** [Your repo URL]
- **Email:** [Your support email]
- **Docs:** [Your website]

---

## 🎓 Example Questions to Try

### General Knowledge
- "Explain artificial intelligence in simple terms"
- "What are the main causes of climate change?"
- "Tell me about ancient Rome"

### Coding
- "Write a Python function to sort a list"
- "Explain recursion with examples"
- "Debug this code: [paste your code]"

### Writing
- "Write a professional email to reschedule a meeting"
- "Create a bullet-point summary of [topic]"
- "Improve this paragraph: [paste text]"

### Creative
- "Give me 10 blog post ideas about [topic]"
- "Write a short story about [theme]"
- "Create a recipe using [ingredients]"

### Analysis (with CSV)
- Upload data.csv → "Analyze this sales data"
- "Show trends in this dataset"
- "Create visualizations for this data"

---

## 📊 Technical Info

### What's Inside

- **Python 3.11** runtime
- **FastAPI** backend
- **React** frontend
- **SQLite** database
- **Machine learning** libraries

### Ports Used

- **8000** - NemhemAI app
- **11434** - Ollama API

### Installation Size

- **NemhemAI:** ~1.5 GB
- **Ollama:** ~500 MB
- **AI Models:** 2-8 GB each

---

## ✅ Quick Reference

### Installation Checklist
- [ ] Windows 10/11 (64-bit)
- [ ] 4+ GB RAM available
- [ ] 3+ GB disk space
- [ ] Internet connection
- [ ] Install Ollama
- [ ] Run: `ollama pull llama3`
- [ ] Install NemhemAI
- [ ] Create account
- [ ] Start chatting!

### Files Included
- `NemhemAI-Setup-v1.0.0.exe` - Installer (~600 MB)
- This README file
- User guide (in app folder after install)

---

## 🎉 You're Ready!

**Your personal AI assistant is just 3 steps away:**

1. Install Ollama + download model
2. Run NemhemAI installer
3. Start chatting!

**Questions?** Check the troubleshooting section above.

---

**Version:** 1.0.0  
**Release Date:** November 2025  
**Supported OS:** Windows 10/11 (64-bit)

**Thank you for using NemhemAI!** 🤖💙

---

## 📄 License

[Add your license here]

Copyright © 2025 [Your Name/Company]
