#!/bin/bash

echo "===================================="
echo "NemhemAI - Mac App Build Script"
echo "===================================="
echo ""

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js is not installed!"
    echo "Please install Node.js from https://nodejs.org/"
    exit 1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed!"
    echo "Please install Python 3 from https://www.python.org/"
    exit 1
fi

echo "[Step 1/5] Cleaning previous builds..."
rm -rf dist/NemhemAI.app
rm -rf build
rm -rf __pycache__
echo "Done!"
echo ""

echo "[Step 2/5] Installing Node.js dependencies..."
npm install
if [ $? -ne 0 ]; then
    echo "ERROR: npm install failed!"
    exit 1
fi
echo "Done!"
echo ""

echo "[Step 3/5] Building React frontend..."
npm run build
if [ $? -ne 0 ]; then
    echo "ERROR: Frontend build failed!"
    exit 1
fi
echo "Done!"
echo ""

echo "[Step 4/5] Installing Python dependencies..."
pip3 install -r backend/requirements.txt
pip3 install pyinstaller
echo "Done!"
echo ""

echo "[Step 5/5] Building Mac App with PyInstaller..."
pyinstaller mac_build.spec --clean --noconfirm
if [ $? -ne 0 ]; then
    echo "ERROR: PyInstaller build failed!"
    exit 1
fi
echo "Done!"
echo ""

echo "===================================="
echo "Build completed successfully!"
echo "===================================="
echo ""
echo "Your app is located at: dist/NemhemAI.app"
echo ""
echo "To create a DMG installer (optional):"
echo "  1. Install create-dmg: brew install create-dmg"
echo "  2. Run: create-dmg dist/NemhemAI.app"
echo ""
