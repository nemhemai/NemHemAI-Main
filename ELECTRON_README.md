# 🎯 NemhemAI - Electron Desktop Application

## Overview

Your NemhemAI project now supports building cross-platform desktop applications using **Electron**! This keeps your existing Python FastAPI backend while providing a professional desktop experience.

## 🌟 Key Features

- ✅ **Cross-Platform**: Build for Windows, macOS, and Linux
- ✅ **Python Backend Included**: Your FastAPI backend is bundled automatically
- ✅ **Professional Installers**: NSIS (Windows), DMG (Mac), DEB/RPM (Linux)
- ✅ **Native Menus**: Full desktop application menus
- ✅ **Hot Reload**: Development mode with instant updates
- ✅ **Auto-Updates Ready**: Can be configured for automatic updates
- ✅ **No Dependencies**: Users don't need Python or Node.js installed

## 📋 Prerequisites

Before building, ensure you have:

- **Node.js 18+** ([Download](https://nodejs.org/))
- **Python 3.8+** ([Download](https://www.python.org/))
- **Git** (optional)

## 🚀 Quick Start (3 Steps)

### Step 1: Install Dependencies

```bash
npm install
pip install -r backend/requirements.txt
```

### Step 2: Test in Development

```bash
npm run electron:dev
```

This will:

1. Start your React frontend (Vite)
2. Start your Python backend (FastAPI)
3. Open the Electron window

### Step 3: Build Installer

**Windows:**

```bash
npm run electron:build:win
```

**macOS:**

```bash
npm run electron:build:mac
```

**Linux:**

```bash
npm run electron:build:linux
```

Your installer will be in `electron-dist/` folder!

## 📦 Available Scripts

| Command                        | Description                          |
| ------------------------------ | ------------------------------------ |
| `npm run electron:dev`         | Run in development mode (hot reload) |
| `npm run electron:build:win`   | Build Windows installer              |
| `npm run electron:build:mac`   | Build macOS installer                |
| `npm run electron:build:linux` | Build Linux packages                 |
| `npm run electron:build:all`   | Build for all platforms              |
| `npm run electron`             | Run production build locally         |

## 🏗️ Project Structure

```
nemhemai/
├── electron/                    # Electron configuration
│   ├── main.js                 # Main process (app logic)
│   ├── preload.js              # Security preload
│   └── build/                  # Build resources
│       ├── icon.ico            # Windows icon (add yours)
│       ├── icon.icns           # macOS icon (add yours)
│       └── icon.png            # Linux icon (add yours)
│
├── backend/                     # Python FastAPI backend
│   ├── main.py                 # Backend server
│   └── requirements.txt        # Python dependencies
│
├── src/                        # React frontend
│   └── ...                     # Your React components
│
├── dist/                       # Built frontend (after npm run build)
├── electron-dist/              # Built Electron apps
│
├── electron-builder.json       # Build configuration
├── package.json               # Node dependencies & scripts
│
├── build-electron.bat         # Windows quick build script
│
└── Documentation/
    ├── ELECTRON_SETUP_COMPLETE.md
    ├── ELECTRON_BUILD_GUIDE.md
    └── ELECTRON_QUICK_START.md
```

## 🎨 Customization

### 1. Application Name & Version

Edit `electron-builder.json`:

```json
{
  "productName": "YourAppName",
  "version": "1.0.0",
  "description": "Your app description",
  "author": "Your Name"
}
```

### 2. Application Icons

Create and add icons to `electron/build/`:

- **Windows**: `icon.ico` (256x256 or multi-size)
- **macOS**: `icon.icns` (512x512+)
- **Linux**: `icon.png` (512x512 PNG)

**Tools to create icons:**

- [iConvert Icons](https://iconverticons.com/)
- [CloudConvert](https://cloudconvert.com/)
- Photoshop/GIMP

### 3. Window Settings

Edit `electron/main.js`:

```javascript
mainWindow = new BrowserWindow({
  width: 1400, // Change width
  height: 900, // Change height
  minWidth: 1024, // Minimum width
  minHeight: 768, // Minimum height
  // ... other settings
});
```

### 4. Application Menu

Edit the `menuTemplate` in `electron/main.js` to customize menus.

## 🔧 How It Works

### Architecture

```
┌─────────────────────────────────────┐
│     Electron Main Process           │
│  (electron/main.js)                 │
│                                     │
│  1. Starts Python Backend           │
│  2. Waits for Backend Ready         │
│  3. Creates Application Window      │
│  4. Loads React Frontend            │
└─────────────────────────────────────┘
         │                    │
         ▼                    ▼
┌──────────────────┐   ┌──────────────────┐
│  Python Backend  │   │  Electron Window │
│  (FastAPI)       │◄──┤  (React App)     │
│  Port: 8000      │   │                  │
└──────────────────┘   └──────────────────┘
```

### Development vs Production

**Development Mode** (`npm run electron:dev`):

- Frontend: Vite dev server (http://localhost:5173)
- Backend: Local Python
- Hot reload enabled

**Production Mode** (built app):

- Frontend: Bundled static files
- Backend: Bundled with app
- Single installer package

## 📊 Build Outputs

### Windows

- `NemhemAI-1.0.0-win-x64.exe` - NSIS Installer
- `NemhemAI-1.0.0-win-x64-portable.exe` - Portable version

### macOS

- `NemhemAI-1.0.0-mac-x64.dmg` - Intel Mac installer
- `NemhemAI-1.0.0-mac-arm64.dmg` - Apple Silicon installer
- `NemhemAI-1.0.0-mac-x64.zip` - ZIP archive

### Linux

- `NemhemAI-1.0.0-linux-x64.AppImage` - Universal Linux app
- `NemhemAI-1.0.0-linux-x64.deb` - Debian/Ubuntu package
- `NemhemAI-1.0.0-linux-x64.rpm` - Fedora/RedHat package

## 🐛 Troubleshooting

### "Backend failed to start"

**Cause**: Python not found or dependencies missing

**Solution**:

```bash
python --version  # Check Python is installed
pip install -r backend/requirements.txt
```

### "Module not found" errors

**Cause**: Node dependencies not installed

**Solution**:

```bash
rm -rf node_modules package-lock.json
npm install
```

### Build fails

**Cause**: Various reasons

**Solutions**:

1. Ensure frontend is built: `npm run build`
2. Check disk space (need ~2GB free)
3. Clear cache: `rm -rf electron-dist`
4. Reinstall: `npm install`

### Large file size

**Cause**: Electron bundles Chromium

**Solutions**:

1. Exclude unnecessary files in `electron-builder.json`
2. Remove unused Python packages
3. Use compression (enabled by default)

### App won't start after building

**Cause**: Backend files missing or Python path issues

**Solutions**:

1. Check `backend/` folder is complete
2. Verify `electron-builder.json` includes backend files
3. Check console logs for errors

## 🚀 Distribution

### Windows

**NSIS Installer** (recommended):

- Professional installer with uninstaller
- Creates Start Menu shortcuts
- Allows custom install location

**Portable EXE**:

- Single executable
- No installation required
- Good for USB drives

### macOS

**DMG Installer** (recommended):

- Standard Mac installer format
- Drag-and-drop installation
- Professional appearance

**Note**: For public distribution, you need:

- Apple Developer account ($99/year)
- Code signing certificate
- Notarization

### Linux

**AppImage** (recommended):

- Universal format
- Works on most distros
- No installation required

**DEB/RPM**:

- For specific distributions
- Integrates with package managers

## 🔐 Security

### Code Signing

**Windows**:

- Get a code signing certificate
- Add to `electron-builder.json`:

```json
"win": {
  "certificateFile": "path/to/cert.pfx",
  "certificatePassword": "password"
}
```

**macOS**:

- Requires Apple Developer account
- Configure in `electron-builder.json`:

```json
"mac": {
  "identity": "Developer ID Application: Your Name (XXXXXXXXXX)"
}
```

## 📈 Advanced Features

### Auto-Updates

Install electron-updater:

```bash
npm install electron-updater
```

Configure update server in `electron-builder.json` and add update logic to `main.js`.

### Custom Protocols

Handle custom URLs (e.g., `nemhemai://`):

1. Register in `electron-builder.json`
2. Handle in `main.js` with `app.setAsDefaultProtocolClient()`

### Crash Reporting

Add crash reporting with services like:

- Sentry
- BugSnag
- Electron's built-in crash reporter

## 📚 Resources

- [Electron Documentation](https://www.electronjs.org/docs)
- [electron-builder Docs](https://www.electron.build/)
- [Electron Security](https://www.electronjs.org/docs/latest/tutorial/security)

## 🆚 PyInstaller vs Electron

| Feature            | PyInstaller                   | Electron        |
| ------------------ | ----------------------------- | --------------- |
| **Cross-platform** | ❌ (requires separate builds) | ✅ Easy         |
| **File Size**      | ~100-200 MB                   | ~150-300 MB     |
| **Development**    | Slow (rebuild required)       | ✅ Hot reload   |
| **Native UI**      | Limited                       | ✅ Full support |
| **Updates**        | Manual                        | ✅ Auto-update  |
| **Ecosystem**      | Python-focused                | ✅ Mature       |
| **Performance**    | Good                          | ✅ Excellent    |

## 🎉 Success!

You now have a professional cross-platform desktop application setup!

**Next steps:**

1. ✅ Run `npm install` (if not done)
2. ✅ Test with `npm run electron:dev`
3. ✅ Add custom icons
4. ✅ Build with `npm run electron:build:win`
5. ✅ Distribute your app!

**Questions?** Check the documentation:

- `ELECTRON_QUICK_START.md` - Quick reference
- `ELECTRON_BUILD_GUIDE.md` - Detailed guide
- `ELECTRON_SETUP_COMPLETE.md` - What was created

Happy building! 🚀
