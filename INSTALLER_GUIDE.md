# Creating an Installer for NemhemAI

## 🎯 Quick Start

1. **Download Inno Setup**: https://jrsoftware.org/isdl.php
2. **Build the EXE**: Run `build.bat` or `pyinstaller main.exe.spec`
3. **Compile Installer**: Open `installer.iss` in Inno Setup and click "Compile"
4. **Done!** Your installer will be in `installer_output\` folder

---

## 📋 Prerequisites

### 1. Install Inno Setup
- Download from: https://jrsoftware.org/isdl.php
- Install the latest version (6.0+)
- This is free and open-source

### 2. Build Your EXE First
```powershell
# Make sure your EXE is built
.\build.bat

# Or manually
pyinstaller main.exe.spec --clean --noconfirm
```

Your `dist\NemhemAI.exe` should exist before creating the installer.

---

## 🔨 Creating the Installer

### Method 1: Using Inno Setup GUI (Recommended)

1. **Open Inno Setup Compiler**
   - Find it in Start Menu after installation

2. **Open the script**
   - File → Open → Select `installer.iss`

3. **Compile**
   - Click "Build" → "Compile" (or press F9)
   - Watch the compilation progress

4. **Get your installer**
   - Look in `installer_output\` folder
   - File will be named: `NemhemAI-Setup-v1.0.0.exe`

### Method 2: Command Line

```powershell
# Compile using Inno Setup command line compiler
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

---

## 📦 What the Installer Does

### Installation Process:
1. ✅ Checks if Ollama is installed
2. ✅ Copies NemhemAI.exe to Program Files
3. ✅ Creates Start Menu shortcuts
4. ✅ Optionally creates Desktop shortcut
5. ✅ Creates necessary directories with proper permissions
6. ✅ Copies documentation files
7. ✅ Creates uninstaller

### Created Directories:
- `C:\Program Files\NemhemAI\` - Main application
- `C:\Program Files\NemhemAI\databases\` - Database storage
- `C:\Program Files\NemhemAI\csv_uploads\` - CSV file uploads
- `C:\Program Files\NemhemAI\uploads\` - Document uploads
- `C:\Program Files\NemhemAI\docs\` - Documentation

### Created Shortcuts:
- Start Menu → NemhemAI
- Start Menu → User Guide
- Start Menu → Uninstall NemhemAI
- Desktop → NemhemAI (optional)

---

## ⚙️ Customizing the Installer

### Change App Version
Edit `installer.iss`:
```pascal
#define MyAppVersion "1.0.0"  <- Change this
```

### Change Company Name
```pascal
#define MyAppPublisher "Your Company"  <- Change this
```

### Add Custom Icon
1. Create or get an `.ico` file
2. Edit `installer.iss`:
```pascal
SetupIconFile=path\to\your\icon.ico
```

### Change Installation Directory
```pascal
DefaultDirName={autopf}\{#MyAppName}
; Change to: DefaultDirName={userpf}\{#MyAppName}
; For user directory instead of Program Files
```

### Add License Agreement
1. Create `LICENSE.txt` in project root
2. Edit `installer.iss`:
```pascal
LicenseFile=LICENSE.txt
```

---

## 🎨 Advanced Customization

### Add Splash Screen
```pascal
[Setup]
; Add these lines
WizardImageFile=splash.bmp
WizardSmallImageFile=smalllogo.bmp
```

### Multiple Languages
```pascal
[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
```

### Custom Installation Steps
You can modify the `[Code]` section to add:
- Download additional components
- Check system requirements
- Configure application settings
- Register file associations

---

## 📊 Installer Size

Expected installer size: **~500-700 MB** (compressed)
- This includes your full EXE (~1.4 GB)
- Inno Setup compresses it well with LZMA2

---

## 🧪 Testing the Installer

### Test Checklist:

1. **Fresh Install**
   - [ ] Run installer on clean system
   - [ ] Check if Ollama check works
   - [ ] Verify all files copied correctly
   - [ ] Test desktop shortcut
   - [ ] Test Start Menu shortcuts

2. **Application Launch**
   - [ ] Launch from Start Menu
   - [ ] Launch from Desktop
   - [ ] Verify browser opens
   - [ ] Check if port 8000 works

3. **Uninstall**
   - [ ] Run uninstaller
   - [ ] Verify all files removed
   - [ ] Check shortcuts removed
   - [ ] Check Start Menu cleaned up

4. **Upgrade Install**
   - [ ] Install v1.0
   - [ ] Install v1.1 over it
   - [ ] Verify settings preserved

---

## 🚀 Distribution

### Share Your Installer:

1. **The installer is standalone**
   - Single `.exe` file
   - No dependencies needed
   - Users just double-click to install

2. **Upload to:**
   - Your website
   - GitHub Releases
   - Google Drive / Dropbox
   - Company network share

3. **User Instructions:**
   ```
   1. Download NemhemAI-Setup-v1.0.0.exe
   2. Run the installer
   3. Follow the installation wizard
   4. Install Ollama if prompted
   5. Launch NemhemAI from Start Menu
   ```

---

## 🔐 Code Signing (Optional but Recommended)

For professional distribution, sign your installer:

### Why Sign?
- No Windows SmartScreen warnings
- Users trust signed software
- Professional appearance

### How to Sign:
1. Get a code signing certificate ($100-500/year)
2. Add to Inno Setup script:
```pascal
[Setup]
SignTool=signtool
SignedUninstaller=yes
```

3. Configure signtool:
```pascal
[Setup]
SignTool=signtool sign /f "certificate.pfx" /p "password" /t "http://timestamp.digicert.com" $f
```

---

## 🐛 Troubleshooting

### Issue: "Cannot find NemhemAI.exe"
**Solution**: Build your EXE first with `build.bat`

### Issue: "Inno Setup not found"
**Solution**: Install from https://jrsoftware.org/isdl.php

### Issue: Compilation errors
**Solution**: Check file paths in `installer.iss` are correct

### Issue: Installer too large
**Solution**: This is normal - your app is ~1.4GB. The installer compresses it to ~500-700MB

### Issue: SmartScreen warning
**Solution**: 
- Get a code signing certificate, or
- Users can click "More info" → "Run anyway"

---

## 📝 Batch Script for Easy Building

Create `build-installer.bat`:
```batch
@echo off
echo ====================================
echo NemhemAI - Complete Build Script
echo ====================================
echo.

echo [1/3] Building EXE...
call build.bat
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: EXE build failed!
    pause
    exit /b 1
)

echo.
echo [2/3] Compiling Installer...
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Installer compilation failed!
    pause
    exit /b 1
)

echo.
echo [3/3] Done!
echo ====================================
echo Installer created successfully!
echo ====================================
echo.
echo Location: installer_output\NemhemAI-Setup-v1.0.0.exe
echo.
pause
```

---

## 📚 Additional Resources

- **Inno Setup Documentation**: https://jrsoftware.org/ishelp/
- **Example Scripts**: https://jrsoftware.org/isinfo.php
- **Community Forum**: https://groups.google.com/g/innosetup

---

## ✨ Summary

You now have:
- ✅ Professional installer script (`installer.iss`)
- ✅ Ollama detection during installation
- ✅ Automatic shortcut creation
- ✅ Proper directory structure
- ✅ Clean uninstallation
- ✅ User-friendly installation wizard

**Your users get a professional installation experience!**

---

*Last Updated: November 2025*
