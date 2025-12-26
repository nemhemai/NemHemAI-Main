@echo off
echo ====================================
echo NemhemAI - Complete Installer Build
echo ====================================
echo.

REM Check if Inno Setup is installed
set "INNO_PATH=F:\Inno Setup 6\ISCC.exe"
if not exist "%INNO_PATH%" (
    echo ERROR: Inno Setup not found!
    echo Please download and install Inno Setup from:
    echo https://jrsoftware.org/isdl.php
    echo.
    pause
    exit /b 1
)

REM Step 1: Build the EXE with low memory mode
echo [Step 1/2] Building NemhemAI.exe (Low Memory Mode)...
echo.
call build-lowmem.bat
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: EXE build failed!
    pause
    exit /b 1
)

REM Check if EXE exists (now in directory mode: dist\NemhemAI\NemhemAI.exe)
if not exist "dist\NemhemAI\NemhemAI.exe" (
    echo.
    echo ERROR: NemhemAI.exe not found in dist\NemhemAI folder!
    echo Make sure build-lowmem.bat completed successfully.
    pause
    exit /b 1
)

echo.
echo ====================================
echo EXE built successfully!
echo ====================================
echo.
echo Output: dist\NemhemAI\NemhemAI.exe (Directory Mode)
echo.

REM Step 2: Build the installer
echo [Step 2/2] Creating installer with Inno Setup...
echo.
"%INNO_PATH%" installer.iss
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Installer compilation failed!
    pause
    exit /b 1
)

echo.
echo ====================================
echo Build Complete! 
echo ====================================
echo.
echo Your installer is ready:
echo   Location: installer_output\NemhemAI-Setup-v1.0.0.exe
echo.
echo Folder sizes:
dir /s "dist\NemhemAI" | find "File(s)"
for %%F in (installer_output\NemhemAI-Setup-v1.0.0.exe) do echo   Installer: %%~zF bytes (%%~zF / 1048576 MB)
echo.
echo The installer will package the entire dist\NemhemAI\ folder.
echo You can now distribute the installer to users!
echo.
pause
