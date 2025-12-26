# NemhemAI Electron Desktop Application

## 🚀 Quick Start Guide

This guide will help you build a cross-platform desktop application using Electron with your existing Python backend.

## Prerequisites

Before you begin, ensure you have:

- ✅ **Node.js 18+** installed ([Download](https://nodejs.org/))
- ✅ **Python 3.8+** installed ([Download](https://www.python.org/))
- ✅ **Git** (optional, for version control)

## Installation

### 1. Install Dependencies

First, install all Node.js dependencies including Electron:

```bash
npm install
```

This will install:

- Electron
- electron-builder (for packaging)
- All other required dependencies

### 2. Install Python Dependencies

Make sure your Python backend dependencies are installed:

```bash
pip install -r backend/requirements.txt
```

## Development

### Running in Development Mode

To run the Electron app in development mode:

```bash
npm run electron:dev
```

This will:

1. Start the Vite development server (React frontend)
2. Wait for it to be ready
3. Launch Electron with the Python backend

**Note:** The Python backend will start automatically when you run the Electron app.

### Development Tips

- **Hot Reload**: The frontend supports hot reload during development
- **DevTools**: Press `Ctrl+Shift+I` (Windows/Linux) or `Cmd+Option+I` (Mac) to open DevTools
- **Backend Logs**: Check the terminal for Python backend logs
- **Frontend Logs**: Check the Electron DevTools console

## Building for Production

### Build for Windows

```bash
npm run electron:build:win
```

This creates:

- **NSIS Installer**: `electron-dist/NemhemAI-1.0.0-win-x64.exe`
- **Portable EXE**: `electron-dist/NemhemAI-1.0.0-win-x64-portable.exe`

### Build for macOS

```bash
npm run electron:build:mac
```

This creates:

- **DMG Installer**: `electron-dist/NemhemAI-1.0.0-mac-x64.dmg` (Intel)
- **DMG Installer**: `electron-dist/NemhemAI-1.0.0-mac-arm64.dmg` (Apple Silicon)
- **ZIP Archive**: `electron-dist/NemhemAI-1.0.0-mac-x64.zip`

### Build for Linux

```bash
npm run electron:build:linux
```

This creates:

- **AppImage**: `electron-dist/NemhemAI-1.0.0-linux-x64.AppImage`
- **DEB Package**: `electron-dist/NemhemAI-1.0.0-linux-x64.deb`
- **RPM Package**: `electron-dist/NemhemAI-1.0.0-linux-x64.rpm`

### Build for All Platforms

```bash
npm run electron:build:all
```

**Note:** Building for macOS requires a Mac. Building for Windows can be done on Windows or Mac (with Wine).

## Project Structure

```
nemhemai/
├── electron/                    # Electron-specific files
│   ├── main.js                 # Main process (manages app window & backend)
│   ├── preload.js              # Preload script (security)
│   └── build/                  # Build resources (icons, etc.)
│       ├── icon.ico            # Windows icon
│       ├── icon.icns           # macOS icon
│       └── icon.png            # Linux icon
├── backend/                     # Python FastAPI backend
│   ├── main.py                 # Backend server
│   └── requirements.txt        # Python dependencies
├── src/                        # React frontend source
├── dist/                       # Built frontend (after npm run build)
├── electron-dist/              # Built Electron apps
├── electron-builder.json       # Electron builder configuration
└── package.json               # Node.js dependencies & scripts
```

## How It Works

### Architecture

````
┌─────────────────────────────────────┐
│     Electron Main Process           │
│  (electron/main.js)                 │
│                                     │
│  1. Starts Python Backend           │
│  2. Waits for Backend Ready         │
│  3. Creates Application Window      │
│  4. Loads Frontend                  │
└─────────────────────────────────────┘
         │                    │
         ▼                    ▼
┌──────────────────┐   ┌──────────────────┐
│  Python Backend  │   │  Electron Window │
│  (FastAPI)       │◄──┤  (React App)     │
│  Port: 8000      │   │                  │
└──────────────────┘   └──────────────────┘
- Backend: Bundled with the app (in `resources/backend/`)
- Electron loads the backend URL which serves the frontend

## Customization

### Application Name & Version

Edit `electron-builder.json`:

```json
{
  "productName": "YourAppName",
  "version": "1.0.0",
  "description": "Your app description"
}
````

### Application Icon

Replace the icons in `electron/build/`:

- **Windows**: `icon.ico` (256x256 or multi-size)
- **macOS**: `icon.icns` (512x512 recommended)
- **Linux**: `icon.png` (512x512 PNG)

You can use online tools like [iConvert Icons](https://iconverticons.com/) to create these.

### Window Size & Settings

Edit `electron/main.js`:

```javascript
mainWindow = new BrowserWindow({
  width: 1400, // Change window width
  height: 900, // Change window height
  minWidth: 1024, // Minimum width
  minHeight: 768, // Minimum height
  // ... other settings
});
```

### Menu Customization

Edit the `menuTemplate` in `electron/main.js` to add/remove menu items.

## Troubleshooting

### Backend Not Starting

**Issue**: "Backend failed to start within timeout"

**Solutions**:

1. Check if Python is installed: `python --version`
2. Install backend dependencies: `pip install -r backend/requirements.txt`
3. Check backend logs in the terminal
4. Increase timeout in `electron/main.js` (line with `maxAttempts`)

### Build Errors

**Issue**: electron-builder fails

**Solutions**:

1. Make sure you ran `npm run build` first
2. Check that all dependencies are installed: `npm install`
3. For Windows builds on Mac, install Wine
4. Clear cache: `rm -rf electron-dist node_modules && npm install`

### Python Not Found in Production

**Issue**: Built app can't find Python

**Solutions**:

1. The app bundles Python from `backend/` folder
2. Make sure `backend/` contains all necessary files
3. Check `electron-builder.json` extraResources configuration

### Large File Size

**Issue**: The built app is very large

**Solutions**:

1. Exclude unnecessary files in `electron-builder.json`
2. Remove unused Python packages
3. Use `asar` compression (enabled by default)
4. Consider using PyInstaller for a smaller Python bundle

## Advanced Configuration

### Code Signing (macOS)

For distributing on macOS, you need to sign your app:

1. Get an Apple Developer account
2. Create certificates
3. Add to `electron-builder.json`:

```json
"mac": {
  "identity": "Your Name (XXXXXXXXXX)",
  "hardenedRuntime": true
}
```

### Auto-Updates

To add auto-update functionality:

1. Install `electron-updater`: `npm install electron-updater`
2. Configure update server in `electron-builder.json`
3. Add update logic to `electron/main.js`

### Custom Protocols

To handle custom URL protocols (e.g., `nemhemai://`):

1. Register protocol in `electron-builder.json`
2. Handle in `electron/main.js` with `app.setAsDefaultProtocolClient()`

## Distribution

### Windows

- **NSIS Installer**: Best for most users, includes uninstaller
- **Portable**: Single EXE, no installation required

### macOS

- **DMG**: Standard macOS installer format
- **ZIP**: For manual installation

### Linux

- **AppImage**: Universal, works on most distros
- **DEB**: For Debian/Ubuntu
- **RPM**: For Fedora/RedHat

## Scripts Reference

| Command                        | Description                             |
| ------------------------------ | --------------------------------------- |
| `npm run electron`             | Run Electron (requires built frontend)  |
| `npm run electron:dev`         | Run in development mode with hot reload |
| `npm run electron:build`       | Build for current platform              |
| `npm run electron:build:win`   | Build for Windows                       |
| `npm run electron:build:mac`   | Build for macOS                         |
| `npm run electron:build:linux` | Build for Linux                         |
| `npm run electron:build:all`   | Build for all platforms                 |
| `npm run pack`                 | Package without creating installer      |
| `npm run dist`                 | Create distributable packages           |

## Support

For issues:

1. Check the [Electron Documentation](https://www.electronjs.org/docs)
2. Check the [electron-builder Documentation](https://www.electron.build/)
3. Review backend logs in the terminal
4. Open DevTools to check frontend errors

## License

MIT License - See LICENSE file for details
