@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (echo Execute INSTALAR_WINDOWS.bat primeiro & pause & exit /b 1)
".venv\Scripts\python.exe" -m pip install --upgrade -r requirements.txt
echo Atualizacao concluida. Reinicie MusicSense.
pause
