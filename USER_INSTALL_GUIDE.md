# NemhemAI Installation Guide for Users

## System Requirements

- **Operating System**: Windows 10 or later
- **Python**: Version 3.11 or later
- **Internet Connection**: Required for first-time setup
- **Disk Space**: At least 5 GB free space

## Installation Steps

### Step 1: Install Python (if not already installed)

1. Download Python from [python.org](https://www.python.org/downloads/)
2. Run the installer
3. ✅ **IMPORTANT**: Check "Add Python to PATH" during installation
4. Complete the installation

To verify Python is installed, open Command Prompt and type:

```bash
python --version
```

You should see: `Python 3.11.x` or later

### Step 2: Install NemhemAI

1. Download `NemhemAI-Setup.exe`
2. Double-click to run the installer
3. Follow the installation wizard
4. Choose installation location (or use default)
5. Click "Install"

### Step 3: First Launch (One-Time Setup)

1. Launch NemhemAI from the Start Menu or Desktop shortcut
2. A setup window will appear: **"🚀 Setting up NemhemAI"**
3. Wait while dependencies are installed (5-10 minutes)
   - This happens **only once**
   - Progress is shown on screen
   - Internet connection required
4. The app will open automatically when setup completes

### Step 4: Enjoy!

NemhemAI is now ready to use! Future launches will be instant.

## Troubleshooting

### "Python not found" Error

**Solution**: Install Python 3.11+ and make sure "Add to PATH" was checked.

To fix:

1. Uninstall Python
2. Reinstall Python
3. ✅ Check "Add Python to PATH"
4. Restart NemhemAI

### Setup Takes Too Long

The first-time setup downloads and installs many Python libraries. This is normal and depends on your internet speed.

**Typical times**:

- Fast internet (100+ Mbps): 5-7 minutes
- Medium internet (50 Mbps): 8-12 minutes
- Slow internet (10 Mbps): 15-20 minutes

### Setup Failed

If setup fails:

1. Close NemhemAI
2. Open Command Prompt as Administrator
3. Run:
   ```bash
   cd %APPDATA%\NemhemAI
   python -m pip install -r requirements.txt
   ```
4. Restart NemhemAI

### App Won't Start

1. Make sure Python is installed: `python --version`
2. Try resetting the setup:
   - Open File Explorer
   - Navigate to: `%APPDATA%\NemhemAI`
   - Delete the `.setup_complete` file
   - Restart NemhemAI

## Uninstallation

1. Go to Windows Settings → Apps
2. Find "NemhemAI"
3. Click "Uninstall"

To completely remove all data:

1. Delete: `%APPDATA%\NemhemAI`
2. Delete: `%LOCALAPPDATA%\NemhemAI`

## Support

For issues or questions, please contact support or visit our documentation.

---

**Note**: The first launch requires internet connection and takes 5-10 minutes for setup. Subsequent launches are instant!
