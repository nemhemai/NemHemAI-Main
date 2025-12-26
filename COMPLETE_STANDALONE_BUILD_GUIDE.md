# Complete Standalone Installer Build Guide

## Overview

This guide shows you how to create a **100% standalone installer** that includes:

- ✅ Embedded Python (no external install needed)
- ✅ All Python modules pre-installed
- ✅ Auto-installs Ollama on first run
- ✅ Works on any Windows PC (no prerequisites!)

## Build Process

### Step 1: Create Portable Python Environment

Run the script to create a self-contained Python with all dependencies:

```bash
create-portable-python.bat
```

**What this does:**

- Downloads Python 3.11.9 embeddable package
- Installs pip
- Installs ALL requirements from `backend/requirements.txt`
- Creates `python-embedded/` folder (~2-3 GB)

**Time required:** 15-30 minutes (depending on internet speed)

**Output:** `python-embedded/` folder containing Python + all modules

### Step 2: Build Frontend

```bash
npm run build
```

**Output:** `dist/` folder with React frontend

### Step 3: Build Electron Installer

```bash
npm run electron:build:win
```

**What gets bundled:**

- Electron app shell
- React frontend (from `dist/`)
- Python backend code
- Portable Python environment (from `python-embedded/`)
- Setup script (`setup_complete.py`)

**Output:**

- `electron-dist/NemhemAI-Setup-{version}.exe` (~2-3 GB)
- `electron-dist/NemhemAI-Portable-{version}.exe`

## What Users Get

### Installation Size

- **Installer download:** ~2-3 GB
- **Installed size:** ~3-4 GB
- **After Ollama install:** ~5-6 GB

### System Requirements

- ✅ Windows 10 64-bit or later
- ✅ Internet connection (for Ollama download only)
- ✅ 10 GB free disk space
- ❌ **NO Python installation needed!**
- ❌ **NO manual module installation needed!**

### Installation Process

1. **User downloads** `NemhemAI-Setup.exe` (~2-3 GB)
2. **User runs installer** → installs to Program Files
3. **User launches app** → first-time setup window appears
4. **Ollama auto-installs** (downloads ~500 MB, takes 2-5 minutes)
5. **App opens** and is ready to use!

## First-Time Setup Details

### What Happens on First Launch

```
┌─────────────────────────────────────┐
│  🚀 Setting up NemhemAI             │
│     [Spinner animation]             │
│                                     │
│  Verifying Python environment...   │
│  ✓ Python environment verified!    │
│                                     │
│  Ollama not found. Installing...   │
│  Downloading Ollama installer...   │
│  Downloading... 45%                 │
│  Installing Ollama...               │
│  Ollama installed successfully!     │
│                                     │
│  Starting Ollama service...         │
│  Ollama service started!            │
│                                     │
│  Setup completed successfully!      │
└─────────────────────────────────────┘
```

**Time:** 2-5 minutes (Ollama download + install)

### What Gets Installed

| Component        | Location                                         | Size    |
| ---------------- | ------------------------------------------------ | ------- |
| Electron App     | `C:\Program Files\NemhemAI\`                     | ~500 MB |
| Python + Modules | `C:\Program Files\NemhemAI\resources\python\`    | ~2-3 GB |
| Backend Code     | `C:\Program Files\NemhemAI\resources\backend\`   | ~50 MB  |
| Ollama           | `C:\Users\{user}\AppData\Local\Programs\Ollama\` | ~500 MB |
| User Data        | `C:\Users\{user}\AppData\Roaming\NemhemAI\`      | Varies  |

## File Structure

### Before Building

```
project/
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   └── ...
├── dist/                    ← Built frontend
├── electron/
│   ├── main.js
│   └── ...
├── python-embedded/         ← Created by create-portable-python.bat
│   ├── python.exe
│   ├── Lib/
│   │   └── site-packages/
│   │       ├── pandas/
│   │       ├── fastapi/
│   │       └── ...
│   └── ...
├── setup_complete.py
└── create-portable-python.bat
```

### After Building

```
electron-dist/
├── NemhemAI-Setup-{version}.exe     ← Give this to users
└── NemhemAI-Portable-{version}.exe
```

### Installed on User's PC

```
C:\Program Files\NemhemAI\
├── NemhemAI.exe
├── resources/
│   ├── app.asar
│   ├── python/              ← Bundled Python + all modules
│   │   ├── python.exe
│   │   └── Lib/site-packages/...
│   ├── backend/
│   │   ├── main.py
│   │   └── ...
│   └── setup_complete.py
└── ...
```

## Build Commands Summary

```bash
# 1. Create portable Python (one-time, 15-30 min)
create-portable-python.bat

# 2. Build frontend
npm run build

# 3. Build installer
npm run electron:build:win
```

## Testing the Installer

### Test in a Clean VM

1. Create a fresh Windows 10/11 VM
2. **DO NOT install Python** (testing standalone capability)
3. Copy `NemhemAI-Setup-{version}.exe` to the VM
4. Run the installer
5. Launch NemhemAI
6. Watch the setup window (Ollama installation)
7. Verify the app works

### Expected Behavior

✅ App installs without errors  
✅ No "Python not found" errors  
✅ Setup window appears on first launch  
✅ Ollama downloads and installs automatically  
✅ App opens and works normally  
✅ Subsequent launches are instant (no setup)

## Advantages of This Approach

### ✅ True Standalone

- **No prerequisites** - works on any Windows 10+ PC
- **No Python installation** needed
- **No manual module installation** needed
- **No Ollama installation** needed (auto-installs)

### ✅ Professional UX

- One-click installer
- Automatic dependency installation
- Progress feedback
- Error handling

### ✅ Reliable

- All dependencies bundled
- No version conflicts
- No internet required (except Ollama download)
- Works offline after first setup

## Disadvantages

### ❌ Large Download

- **Before:** ~150 MB (Python modules installed on first run)
- **After:** ~2-3 GB (everything bundled)

### ❌ Longer Build Time

- Creating portable Python: 15-30 minutes
- Building installer: 5-10 minutes
- **Total:** ~20-40 minutes

### ❌ Larger Disk Space

- Development: Need ~5 GB for `python-embedded/`
- Distribution: ~2-3 GB installer
- User's PC: ~5-6 GB after installation

## When to Use This Approach

**Use this standalone approach when:**

- ✅ Target users are non-technical
- ✅ You want zero prerequisites
- ✅ You want guaranteed compatibility
- ✅ Download size is not a concern
- ✅ You want professional UX

**Use the previous approach (auto-install) when:**

- ✅ Users can install Python
- ✅ Smaller download is important
- ✅ Users have good internet
- ✅ You update frequently

## Troubleshooting

### Build Issues

**"python-embedded folder not found"**

- Run `create-portable-python.bat` first
- Wait for it to complete (15-30 minutes)

**"electron-builder fails"**

- Make sure `python-embedded/` exists
- Check disk space (need ~10 GB free)
- Try running as Administrator

### Runtime Issues

**"Bundled Python not found"**

- Reinstall the application
- Check if `C:\Program Files\NemhemAI\resources\python\` exists

**"Ollama installation failed"**

- Check internet connection
- Run as Administrator
- Manually install Ollama from https://ollama.com

## Distribution

### What to Give Users

1. **NemhemAI-Setup.exe** (~2-3 GB)
2. **Installation guide:**
   ```
   1. Download NemhemAI-Setup.exe
   2. Run the installer
   3. Launch NemhemAI
   4. Wait for first-time setup (2-5 minutes)
   5. Enjoy!
   ```

### System Requirements to Communicate

- Windows 10 64-bit or later
- 10 GB free disk space
- Internet connection (for first-time setup only)

## Summary

You now have a **truly standalone installer** that:

✅ Bundles Python + all modules  
✅ Auto-installs Ollama  
✅ Works on any Windows PC  
✅ Requires no prerequisites  
✅ Provides professional UX

**Trade-off:** Larger download size (~2-3 GB vs ~150 MB)

**Build time:** ~20-40 minutes (one-time Python setup + build)

**User experience:** Download → Install → Launch → Wait 2-5 min → Use!

---

**Your app is now completely self-contained and ready for distribution!** 🎉
