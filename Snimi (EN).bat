@echo off
chcp 65001 >nul
title Snimanje sastanka (EN)
cd /d "%~dp0"
set "PY=%USERPROFILE%\.meeting-minutes-ai\venv\Scripts\python.exe"
if not exist "%PY%" (
  echo Alat nije instaliran. Prvo pokreni instaliraj.bat
  pause
  exit /b 1
)
"%PY%" snimi.py --jezik en %*
echo.
pause