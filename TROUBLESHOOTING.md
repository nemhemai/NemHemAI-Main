# Troubleshooting: App Not Opening (Process Running in Task Manager)

## Problem

After installing the exe, when you run it, the process appears in Task Manager but no window shows up.

## Common Causes & Solutions

### 1. Check the Logs

**Where to find logs:**

- Development: Check the terminal/console where you ran the app
- Production: Logs are in `%APPDATA%\NemhemAI\logs\` (if logging is configured)

**How to run with console output (Production):**

```bash
# Navigate to installation folder
cd "C:\Program Files\NemhemAI"

# Run with console
NemhemAI.exe --enable-logging --v=1
```

### 2. Frontend Build Issue

**Problem:** The `dist/` folder might be missing or incomplete.

**Solution:**

```bash
# Rebuild the frontend
npm run build

# Verify dist folder exists
dir dist

# Should contain: index.html, assets/, etc.
```

### 3. Python Backend Not Starting

**Problem:** Bundled Python or backend script has issues.

**Check:**

1. Does `python-embedded/` folder exist?
2. Run the portable Python manually:
   ```bash
   python-embedded\python.exe backend\main.py
   ```
3. Check for errors

**Solution:**

- Recreate portable Python: `create-portable-python.bat`
- Verify all modules installed correctly

### 4. Missing Preload Script

**Problem:** `electron/setup-preload.js` or `electron/preload.js` missing.

**Check:**

```bash
dir electron\*.js
```

**Should see:**

- main.js
- preload.js
- setup-preload.js

### 5. Path Issues

**Problem:** File paths are incorrect in production.

**Debug:** Add logging to `electron/main.js`:

```javascript
// In createWindow function
console.log("Loading URL:", startUrl);
console.log("File exists:", fs.existsSync(startUrl.replace("file://", "")));
```

### 6. Window Not Showing

**Problem:** Window created but `show: false` and never shows.

**Our Fix:** We added:

- 10-second timeout to force show
- Error handlers to show window on failure
- Better logging

**Manual test:**

```javascript
// In electron/main.js, temporarily change:
show: false  →  show: true
```

### 7. Electron Version Mismatch

**Problem:** Electron version incompatibility.

**Check:**

```bash
npm list electron
```

**Fix:**

```bash
npm install electron@latest --save-dev
npm run electron:build:win
```

## Quick Diagnostic Steps

### Step 1: Run in Development Mode

```bash
npm run electron:dev
```

**If it works in dev but not production:**

- Build issue
- Path issue
- Missing files in bundle

**If it doesn't work in dev either:**

- Code issue
- Dependency issue

### Step 2: Check Task Manager Details

1. Open Task Manager
2. Find "NemhemAI.exe"
3. Right-click → "Go to details"
4. Check:
   - CPU usage (should be >0% initially)
   - Memory usage (should be ~100-200 MB)
   - If it's using 0% CPU and low memory → crashed immediately

### Step 3: Check Event Viewer (Windows)

1. Open Event Viewer
2. Windows Logs → Application
3. Look for errors from "NemhemAI" or "Electron"
4. Check error messages

### Step 4: Test Bundled Python

```bash
cd "C:\Program Files\NemhemAI\resources"
python\python.exe --version
python\python.exe backend\main.py
```

**Expected:** Backend should start on port 8000

### Step 5: Test Frontend Files

```bash
cd "C:\Program Files\NemhemAI\resources"
dir app.asar
```

**Should exist:** `app.asar` file (~50 MB)

## Debugging with Console

### Enable Console Output

Create a batch file to run with console:

**`run-with-console.bat`:**

```batch
@echo off
cd "C:\Program Files\NemhemAI"
NemhemAI.exe --enable-logging --v=1
pause
```

Run this to see console output.

### Add More Logging

Edit `electron/main.js` and add:

```javascript
// At the very top
console.log("=== ELECTRON STARTING ===");
console.log("Process:", process.execPath);
console.log("CWD:", process.cwd());
console.log("Resources:", process.resourcesPath);

// In createWindow
console.log("=== CREATING WINDOW ===");
console.log("Icon path:", iconPath);
console.log("Start URL:", startUrl);

// After window creation
console.log("=== WINDOW CREATED ===");
console.log("Window ID:", mainWindow.id);
```

## Common Error Messages

### "Failed to load URL"

**Cause:** Frontend files missing or path wrong
**Fix:** Rebuild frontend, check `dist/` folder

### "Bundled Python not found"

**Cause:** `python-embedded/` not bundled
**Fix:** Run `create-portable-python.bat`, rebuild installer

### "Backend startup failed"

**Cause:** Python or module issue
**Fix:** Test Python manually, check modules

### "Setup failed"

**Cause:** Ollama installation failed
**Fix:** Install Ollama manually from https://ollama.com

## Force Window to Show

Temporary fix to see what's happening:

**In `electron/main.js`:**

```javascript
mainWindow = new BrowserWindow({
  // ... other options ...
  show: true, // ← Change from false to true
});

// Comment out this:
// mainWindow.once('ready-to-show', () => {
//   mainWindow.show();
// });
```

This will show the window immediately, even if content isn't loaded.

## Nuclear Option: Complete Rebuild

```bash
# 1. Clean everything
rm -rf node_modules
rm -rf dist
rm -rf electron-dist
rm -rf python-embedded

# 2. Reinstall
npm install

# 3. Rebuild Python
create-portable-python.bat

# 4. Rebuild frontend
npm run build

# 5. Rebuild installer
npm run electron:build:win

# 6. Test fresh install
```

## Get Help

If none of these work, collect this information:

1. **Console output** (from run-with-console.bat)
2. **Event Viewer errors**
3. **File structure:**
   ```bash
   tree "C:\Program Files\NemhemAI" /F > structure.txt
   ```
4. **System info:**
   - Windows version
   - Installed Python version (if any)
   - Antivirus software

## Our Recent Fixes

We've added these improvements to help debug:

1. ✅ 10-second timeout to force show window
2. ✅ Error handlers for failed loads
3. ✅ Console logging from renderer process
4. ✅ Better error messages
5. ✅ Window shows even if backend fails
6. ✅ Detailed startup logging

**Try rebuilding with the latest code!**

---

## Quick Fix Checklist

- [ ] Rebuilt frontend (`npm run build`)
- [ ] Verified `dist/` folder exists and has files
- [ ] Recreated portable Python (`create-portable-python.bat`)
- [ ] Verified `python-embedded/` folder exists
- [ ] Rebuilt installer (`npm run electron:build:win`)
- [ ] Tested in development mode first
- [ ] Checked console output
- [ ] Checked Event Viewer
- [ ] Tried forcing window to show
- [ ] Tested on clean VM

If all else fails, the app should at least show an error window now with our improvements!
