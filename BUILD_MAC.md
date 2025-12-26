# Building NemhemAI for macOS

This guide explains how to build the NemhemAI application for macOS.

## Prerequisites

You must be running on a macOS machine to build the Mac version.

1.  **Node.js**: Install from [nodejs.org](https://nodejs.org/).
2.  **Python 3**: Install from [python.org](https://www.python.org/).
3.  **Ollama**: Users will need Ollama installed to use the AI features.

## Application Icon

To have a custom icon for your Mac app:

1.  Create an `.icns` file (you can convert a PNG to ICNS using online tools or `iconutil` on Mac).
2.  Save it as `public/icon.icns`.
3.  The build script will automatically use it.

## Build Instructions

1.  Open a terminal in the project directory.
2.  Make the build script executable:
    ```bash
    chmod +x build-mac.sh
    ```
3.  Run the build script:
    ```bash
    ./build-mac.sh
    ```

This script will:

- Install all dependencies.
- Build the React frontend.
- Package the Python backend and frontend into a `.app` bundle using PyInstaller.

The output will be located at `dist/NemhemAI.app`.

## Creating a DMG Installer

To distribute your app easily, you can create a `.dmg` file.

1.  Install `create-dmg` using Homebrew:
    ```bash
    brew install create-dmg
    ```
2.  Run the following command:
    ```bash
    create-dmg \
      --volname "NemhemAI Installer" \
      --window-pos 200 120 \
      --window-size 800 400 \
      --icon-size 100 \
      --icon "NemhemAI.app" 200 190 \
      --hide-extension "NemhemAI.app" \
      --app-drop-link 600 185 \
      "NemhemAI-Installer.dmg" \
      "dist/NemhemAI.app"
    ```

## Troubleshooting

### "App is damaged and can't be opened"

If you see this error when running the app on another Mac, it's because the app is not notarized by Apple.
To fix this locally (for the user), they can run:

```bash
xattr -cr /Applications/NemhemAI.app
```

For proper distribution, you need to sign and notarize your app with an Apple Developer ID.

### "Ollama not found"

Ensure Ollama is installed and running on the Mac. The app attempts to connect to `localhost:11434`.
