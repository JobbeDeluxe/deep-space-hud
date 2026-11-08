@echo off
setlocal
cd /d "%~dp0"
title DEEP SPACE - HDMI Statuspanel
if exist ".venv\Scripts\python.exe" goto dependencies
py -3 --version >nul 2>&1
if not errorlevel 1 (
  py -3 -m venv .venv
  goto checkenv
)
python --version >nul 2>&1
if not errorlevel 1 (
  python -m venv .venv
  goto checkenv
)
echo Python fehlt. Bitte Python 3.10 oder neuer von https://www.python.org/downloads/windows/ installieren.
echo Beim Installieren "Add python.exe to PATH" aktivieren. Danach START.cmd erneut starten.
pause
exit /b 1
:checkenv
if not exist ".venv\Scripts\python.exe" (
  echo Python-Umgebung konnte nicht erstellt werden. Bitte in einen beschreibbaren Ordner entpacken.
  pause
  exit /b 1
)
:dependencies
".venv\Scripts\python.exe" -c "import psutil, pycaw" >nul 2>&1
if not errorlevel 1 goto run
echo Einmalige Einrichtung der Sensor-Bibliotheken. Dafuer wird Internet benoetigt.
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo Einrichtung fehlgeschlagen. Bitte die Fehlermeldung oben pruefen.
  pause
  exit /b 1
)
:run
".venv\Scripts\python.exe" server.py
if errorlevel 1 pause
