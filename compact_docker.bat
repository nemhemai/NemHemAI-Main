@echo off
echo Shutting down Docker and WSL...
wsl --shutdown

echo.
echo Compacting Docker Virtual Disk... This may take a minute.
(
echo select vdisk file="C:\Users\ayush\AppData\Local\Docker\wsl\disk\docker_data.vhdx"
echo attach vdisk readonly
echo compact vdisk
echo detach vdisk
echo exit
) > "%TEMP%\compact.txt"

diskpart /s "%TEMP%\compact.txt"

echo.
echo Done! Your 10GB should be returned to the C: drive.
pause
