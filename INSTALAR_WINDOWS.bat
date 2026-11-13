@echo off
setlocal
cd /d "%~dp0"
title MusicSense AI - Instalacao
set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not exist "%PY%" (
 echo Python 3.12 nao encontrado. Instale Python 3.12 antes de continuar.
 pause
 exit /b 1
)
if not exist ".venv\Scripts\python.exe" "%PY%" -m venv ".venv"
if errorlevel 1 (echo Falha ao criar ambiente virtual. & pause & exit /b 1)
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check "faster-whisper==1.2.1" argostranslate imageio-ffmpeg yt-dlp
if errorlevel 1 (echo Falha na instalacao. & pause & exit /b 1)
".venv\Scripts\python.exe" instalar_traducao.py
echo Instalacao concluida.
pause

[executed on device: ESCRITORIO (015f09d9-8ae6-4cef-a39b-c7592204d204)]
