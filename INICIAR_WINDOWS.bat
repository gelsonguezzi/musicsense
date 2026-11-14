@echo off
setlocal
cd /d "%~dp0"
title MusicSense AI - Servidor
if not exist ".venv\Scripts\python.exe" (echo Execute INSTALAR_WINDOWS.bat primeiro & pause & exit /b 1)
set "PATH=C:\Program Files\nodejs;%PATH%"
start "" "http://127.0.0.1:8765"
".venv\Scripts\python.exe" -u server.py
pause
