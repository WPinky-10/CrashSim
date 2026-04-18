@echo off
title CrashSim Installer

echo thank you for installing CrashSim!
echo Installing required Python packages...
python -m pip install --upgrade pip
python -m pip install numpy matplotlib openpyxl

echo.
echo.
echo.
echo Installation complete!
echo Congratulations!
echo You can now run CrashSim!
pause