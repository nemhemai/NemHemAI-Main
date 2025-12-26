@echo off
echo ====================================
echo NemhemAI - Electron Development
echo ====================================
echo.

echo Starting Vite development server...
start "Vite Dev Server" cmd /k "npm run dev"

echo Waiting for Vite to start...
timeout /t 8 /nobreak >nul

echo Starting Electron...
npx electron .

echo.
echo Application closed.
pause
