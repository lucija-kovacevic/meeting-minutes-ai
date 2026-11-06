@echo off
chcp 65001 >nul
title meeting-minutes-ai - instalacija
cd /d "%~dp0"
where py >nul 2>nul && (py -3 instaliraj.py %* & goto kraj)
where python >nul 2>nul && (python instaliraj.py %* & goto kraj)
echo Python nije pronaden. Instaliraj Python 3.10+ s https://www.python.org/downloads/
echo (oznaci "Add python.exe to PATH") pa ponovno pokreni instaliraj.bat
:kraj
echo.
pause
