# 🚀 Quick Start - Electron Desktop App

## Step 1: Install Dependencies

```bash
npm install
```

This installs Electron and all required dependencies.

## Step 2: Test in Development Mode

```bash
npm run electron:dev
```

This will:

- Start the React frontend (Vite dev server)
- Launch Electron with your Python backend
- Open the application window

**Note:** Make sure you have Python dependencies installed:

```bash
pip install -r backend/requirements.txt
```

## Step 3: Build for Production

### For Windows:

```bash
npm run electron:build:win
```

Or use the batch file:

```bash
build-electron.bat
```

### For macOS:

```bash
npm run electron:build:mac
```

### For Linux:

```bash
npm run electron:build:linux
```

## Output

Your built applications will be in the `electron-dist/` folder:

- **Windows**: `NemhemAI-1.0.0-win-x64.exe` (installer) and portable version
- **macOS**: `NemhemAI-1.0.0-mac-x64.dmg` and `.zip`
- **Linux**: `NemhemAI-1.0.0-linux-x64.AppImage`, `.deb`, `.rpm`

## Troubleshooting

### "Backend failed to start"

- Make sure Python is installed: `python --version`
- Install backend dependencies: `pip install -r backend/requirements.txt`

### "Module not found"

- Run `npm install` again
- Delete `node_modules` and run `npm install`

### Build fails

- Make sure you ran `npm run build` first (or it runs automatically)
- Check that all dependencies are installed

## Next Steps

1. **Customize Icons**: Add your app icons to `electron/build/` (see ICONS_README.md)
2. **Update App Info**: Edit `electron-builder.json` to change app name, version, etc.
3. **Test**: Run `npm run electron:dev` to test your changes
4. **Build**: Run `npm run electron:build:win` (or mac/linux) to create installer
5. **Distribute**: Share the installer from `electron-dist/` folder

## Full Documentation

See [ELECTRON_BUILD_GUIDE.md](ELECTRON_BUILD_GUIDE.md) for complete documentation.
