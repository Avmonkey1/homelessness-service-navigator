@echo off
echo Installing dependencies...
pip install customtkinter requests pyinstaller

echo.
echo Building WebHunter.exe...
pyinstaller ^
  --onefile ^
  --windowed ^
  --name WebHunter ^
  --add-data "webhunter.py;." ^
  webhunter_gui.py

echo.
echo Done. Your executable is at: dist\WebHunter.exe
pause
