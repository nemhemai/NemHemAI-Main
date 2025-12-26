# NemhemAI - Standalone Installer Guide

## Overview

Your NemhemAI application now uses a **smart auto-installation system** that makes deployment much easier and the installer much smaller.

## How It Works

### First-Time Installation

When a user installs and runs NemhemAI for the first time:

1. **Installer runs** (~100-200MB instead of 5-10GB)
2. **App starts** and detects it's the first run
3. **Setup window appears** with a progress indicator
4. **Python dependencies auto-install** (one-time process, takes 5-10 minutes)
5. **App launches** normally

### Subsequent Runs

- App starts immediately (no setup needed)
- All dependencies are already installed
- Fast startup time

## What's Included

### In the Installer

✅ Electron application shell  
✅ React frontend (built)  
✅ Python backend code  
✅ Requirements.txt  
✅ Setup script  
❌ Python modules (installed on first run)  
❌ Python interpreter (uses system Python)

### System Requirements

Users need to have **Python 3.11 or later** installed on their system.

## Building the Installer

### Step 1: Build Frontend

```bash
npm run build
```

### Step 2: Build Electron Installer

```bash
npm run electron:build:win
```

This creates:

- `NemhemAI-Setup-{version}.exe` - NSIS installer
- `NemhemAI-Portable-{version}.exe` - Portable version

## User Experience

### Installation Flow

1. User downloads `NemhemAI-Setup.exe` (~150MB)
2. User runs installer
3. User launches NemhemAI
4. **First run only**: Setup window appears
   - Shows "Setting up NemhemAI" message
   - Displays progress spinner
   - Shows current installation step
   - Takes 5-10 minutes (depending on internet speed)
5. App opens automatically when setup completes

### What Users See

```
🚀 Setting up NemhemAI
   [Spinner animation]
   Installing Python dependencies...
```

Progress messages include:

- "Installing Python dependencies..."
- "Installing pandas..."
- "Installing fastapi..."
- "Installation complete!"

## Technical Details

### Setup Script (`setup_backend.py`)

- Checks if setup has been completed before
- Creates a flag file: `%APPDATA%/NemhemAI/.setup_complete`
- Runs `pip install -r requirements.txt`
- Only runs once per installation

### Electron Integration

- `electron/main.js` checks for setup flag on startup
- Creates setup window if needed
- Spawns Python setup process
- Shows real-time progress
- Closes setup window when complete

### File Structure

```
NemhemAI/
├── electron/
│   ├── main.js (updated with setup logic)
│   ├── setup-preload.js (new)
│   └── ...
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   └── ...
├── setup_backend.py (new)
└── electron-builder.json (updated)
```

## Advantages

### ✅ Smaller Installer

- **Before**: 5-10 GB (bundled Python + all modules)
- **After**: 100-200 MB (code only)

### ✅ Easier Updates

- Update only changed code
- No need to re-bundle huge libraries
- Faster download for users

### ✅ Better Compatibility

- Uses system Python (better OS integration)
- Modules installed fresh (latest compatible versions)
- Fewer version conflicts

### ✅ User-Friendly

- One-time setup
- Clear progress indication
- Automatic process

## Troubleshooting

### If Setup Fails

Users can manually install requirements:

```bash
cd %APPDATA%\NemhemAI
python -m pip install -r requirements.txt
```

### Reset Setup

Delete the setup flag to re-run setup:

```bash
del %APPDATA%\NemhemAI\.setup_complete
```

### Check Python

Users should verify Python is installed:

```bash
python --version
```

Should show Python 3.11 or later.

## Distribution

### What to Give Users

1. **NemhemAI-Setup.exe** - Main installer
2. **Installation instructions**:
   - Install Python 3.11+ first (if not installed)
   - Run NemhemAI-Setup.exe
   - Wait for first-time setup to complete
   - Enjoy!

### Optional: Bundle Python

If you want to bundle Python (makes it truly standalone):

1. Download Python embeddable package
2. Add to `extraResources` in electron-builder.json
3. Update `electron/main.js` to use bundled Python

## Next Steps

### To Build Now

```bash
# 1. Build frontend
npm run build

# 2. Build installer
npm run electron:build:win
```

### To Test

```bash
# Run in dev mode
npm run electron:dev
```

### To Deploy

1. Build the installer
2. Upload to your distribution platform
3. Provide installation instructions
4. Users download and install

## Summary

Your app now has a **professional, user-friendly installation system** that:

- ✅ Creates small installers
- ✅ Auto-installs dependencies
- ✅ Shows progress to users
- ✅ Works on any PC with Python installed
- ✅ Only runs setup once

The user experience is smooth and modern, similar to professional applications like VS Code or Slack.
