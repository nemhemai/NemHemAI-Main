@echo off
echo ========================================
echo NemhemAI - Debug Mode
echo ========================================
echo.
echo This will run NemhemAI with console output visible.
echo Use this to see error messages if the app won't start.
echo.
pause

REM Run the app with logging enabled
"%~dp0NemhemAI.exe" --enable-logging --v=1

echo.
echo ========================================
echo App closed. Check output above for errors.
echo ========================================
pause
