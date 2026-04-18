@echo off
title CrashSim Uninstaller

echo Removing installed Python packages...

python -m pip uninstall -y numpy matplotlib openpyxl tkinter

echo.
echo Uninstallation complete.

pause