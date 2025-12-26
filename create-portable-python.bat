@echo off
REM Script to create a portable Python environment with all dependencies
REM This creates a self-contained Python that can be bundled with the installer

echo ========================================
echo Creating Portable Python Environment
echo ========================================
echo.

REM Set variables
set PYTHON_VERSION=3.11.9
set PYTHON_EMBED_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/python-%PYTHON_VERSION%-embed-amd64.zip
set PYTHON_DIR=python-embedded
set GET_PIP_URL=https://bootstrap.pypa.io/get-pip.py

echo Step 1: Cleaning up old environment...
if exist %PYTHON_DIR% rmdir /s /q %PYTHON_DIR%
mkdir %PYTHON_DIR%

echo.
echo Step 2: Downloading Python embeddable package...
powershell -Command "Invoke-WebRequest -Uri '%PYTHON_EMBED_URL%' -OutFile 'python-embed.zip'"

echo.
echo Step 3: Extracting Python...
powershell -Command "Expand-Archive -Path 'python-embed.zip' -DestinationPath '%PYTHON_DIR%' -Force"
del python-embed.zip

echo.
echo Step 4: Configuring Python to use pip...
REM Uncomment the import site line in python311._pth
powershell -Command "(Get-Content '%PYTHON_DIR%\python311._pth') -replace '#import site', 'import site' | Set-Content '%PYTHON_DIR%\python311._pth'"

echo.
echo Step 5: Installing pip...
powershell -Command "Invoke-WebRequest -Uri '%GET_PIP_URL%' -OutFile '%PYTHON_DIR%\get-pip.py'"
%PYTHON_DIR%\python.exe %PYTHON_DIR%\get-pip.py
del %PYTHON_DIR%\get-pip.py

echo.
echo Step 6: Upgrading pip...
%PYTHON_DIR%\python.exe -m pip install --upgrade pip

echo.
echo Step 7: Installing all required packages...
echo This will take 10-20 minutes depending on your internet speed...
echo.

%PYTHON_DIR%\python.exe -m pip install -r backend\requirements.txt

echo.
echo Step 8: Cleaning up pip cache to reduce size...
%PYTHON_DIR%\python.exe -m pip cache purge

echo.
echo Step 9: Verifying installation...
%PYTHON_DIR%\python.exe -c "import fastapi, uvicorn, pandas, numpy, matplotlib, sklearn; print('All core packages installed successfully!')"

echo.
echo ========================================
echo Portable Python environment created!
echo Location: %CD%\%PYTHON_DIR%
echo ========================================
echo.
echo You can now bundle this folder with your Electron app.
echo The folder size will be approximately 2-3 GB.
echo.

pause
