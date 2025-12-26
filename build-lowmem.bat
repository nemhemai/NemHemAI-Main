@echo off
echo ========================================
echo NemhemAI - Low Memory Build Script
echo ========================================
echo.

REM Set environment variables to reduce memory usage
set PYTHONHASHSEED=0
set PYINSTALLER_COMPILE_BOOTLOADER=0

echo [1/4] Checking frontend build...
if not exist dist\index.html (
    echo ERROR: Frontend not built! Run: npm run build
    pause
    exit /b 1
)
echo Frontend found!
echo.

echo [2/4] Backing up frontend build...
if exist dist_frontend rmdir /s /q dist_frontend
xcopy dist dist_frontend /E /I /Q
echo Frontend backed up!
echo.

echo [3/4] Cleaning previous PyInstaller build files...
if exist build rmdir /s /q build
REM Only delete PyInstaller output, not frontend
if exist dist\NemhemAI rmdir /s /q dist\NemhemAI
echo Done!
echo.

echo [3/4] Cleaning previous PyInstaller build files...
if exist build rmdir /s /q build
REM Only delete PyInstaller output, not frontend
if exist dist\NemhemAI rmdir /s /q dist\NemhemAI
echo Done!
echo.

echo [4/4] Building with PyInstaller (Low Memory Mode)...
echo This may take 10-15 minutes. Please be patient...
echo.

REM Use --log-level ERROR to reduce console output (saves memory)
pyinstaller main.exe.spec --clean --noconfirm --log-level ERROR

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ========================================
    echo BUILD FAILED!
    echo ========================================
    echo.
    echo Common fixes for memory errors:
    echo 1. Close other programs to free RAM
    echo 2. Restart your computer
    echo 3. Increase virtual memory in Windows settings
    echo 4. Try building without --clean flag
    echo.
    pause
    exit /b 1
)

echo.
echo [5/5] Verifying build...
if exist "dist\NemhemAI\NemhemAI.exe" (
    echo.
    echo ========================================
    echo BUILD SUCCESSFUL!
    echo ========================================
    echo.
    echo Location: dist\NemhemAI\
    echo.
    echo To run: cd dist\NemhemAI
    echo         NemhemAI.exe
    echo.
    echo To create installer: build-installer.bat
    echo.
) else (
    echo ERROR: Build completed but EXE not found!
    echo.
    echo Restoring frontend from backup...
    if exist dist_frontend (
        rmdir /s /q dist
        xcopy dist_frontend dist /E /I /Q
        rmdir /s /q dist_frontend
        echo Frontend restored!
    )
    pause
    exit /b 1
)

REM Clean up backup
if exist dist_frontend rmdir /s /q dist_frontend

pause
