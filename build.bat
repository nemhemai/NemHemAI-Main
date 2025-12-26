@echo off
echo ====================================
echo NemhemAI - EXE Build Script
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

echo [Step 1/5] Cleaning previous builds...
REM Only clean PyInstaller outputs, not frontend dist
if exist dist\NemhemAI rmdir /s /q dist\NemhemAI
if exist build rmdir /s /q build
if exist __pycache__ rmdir /s /q __pycache__
echo Done!
echo.

echo [Step 2/5] Installing Node.js dependencies...
call npm install
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: npm install failed!
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

echo [Step 4/5] Installing Python dependencies...
pip install -r backend\requirements.txt
pip install pyinstaller
echo Done!
echo.

echo [Step 5/5] Building EXE with PyInstaller...
pyinstaller main.exe.spec --clean --noconfirm
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: PyInstaller build failed!
    pause
    exit /b 1
)
echo Done!
echo.

echo ====================================
echo Build completed successfully!
echo ====================================
echo.
echo Your executable is located at: dist\NemhemAI.exe
echo.
echo To run the application:
echo   1. Ensure Ollama is installed and running
echo   2. Double-click dist\NemhemAI.exe
echo.
echo For distribution, copy the NemhemAI.exe file.
echo Users will need Ollama installed on their system.
echo.
pause
