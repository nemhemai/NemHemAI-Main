# 🚀 Quick Start - Build NemhemAI EXE

## 📋 Prerequisites
1. ✅ Python 3.10+
2. ✅ Node.js 18+
3. ✅ Ollama installed

## 🏗️ Build in 3 Commands

```powershell
# Run this from project root
.\build.bat
```

That's it! The automated script will:
- Install dependencies
- Build React frontend
- Create the EXE with PyInstaller

## 📦 Output

Your EXE will be at: **`dist\NemhemAI.exe`**

## ✅ Test It

```powershell
.\dist\NemhemAI.exe
```

Browser should open to http://localhost:8000

## 📚 Full Documentation

- **BUILD_EXE_GUIDE.md** - Complete build instructions
- **BUILD_CHECKLIST.md** - Step-by-step checklist
- **USER_GUIDE.md** - For end users

## 🐛 Troubleshooting

### Build fails?
- Check Node.js: `node --version`
- Check Python: `python --version`
- Check PyInstaller: `pip install pyinstaller`

### EXE doesn't run?
- Install Ollama: https://ollama.com/download
- Run Ollama: `ollama serve`
- Check port 8000 is free

### Need help?
Read **BUILD_EXE_GUIDE.md** for detailed troubleshooting.

---

**Happy Building! 🎉**
