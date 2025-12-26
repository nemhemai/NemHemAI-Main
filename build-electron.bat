@echo off
echo ====================================
echo NemhemAI - Electron Build Script
echo ====================================
echo.

REM Check if Node.js is installed
where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Node.js is not installed!
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)

REM Check if Python is installed
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python is not installed!
    echo Please install Python from https://www.python.org/
    pause
    exit /b 1
)

echo [Step 1/5] Installing Node.js dependencies...
call npm install
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: npm install failed!
    pause
    exit /b 1
)
echo Done!
echo.

echo [Step 2/5] Installing Python dependencies...
pip install -r backend\requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python dependencies installation failed!
    pause
    exit /b 1
)
echo Done!
echo.

echo [Step 3/5] Building React frontend...
call npm run build
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Frontend build failed!
    pause
    exit /b 1
)
echo Done!
echo.

echo [Step 4/5] Building Electron application...
call npm run electron:build:win
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Electron build failed!
    pause
    exit /b 1
)
echo Done!
echo.

echo ====================================
echo Build completed successfully!
echo ====================================
echo.
echo Your installers are located in: electron-dist\
echo.
echo Available files:
echo   - NemhemAI-1.0.0-win-x64.exe (NSIS Installer)
echo   - NemhemAI-1.0.0-win-x64-portable.exe (Portable)
echo.
echo To distribute:
echo   1. Share the installer with users
echo   2. Users can install and run without additional setup
echo   3. Python backend is bundled automatically
echo.
pause
