@echo off
setlocal
cd /d "%~dp0"
title MusicSense AI - Instalar
echo Instalando dependencias locais (sem API paga)
where py >nul 2>&1 || (echo Instale Python 3.11 ou 3.12 de python.org com PATH habilitado & pause & exit /b 1)
py -3 -m venv .venv || (echo Falha no ambiente Python & pause & exit /b 1)
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt || (echo Erro ao instalar bibliotecas & pause & exit /b 1)
".venv\Scripts\python.exe" instalar_traducao.py
echo.
echo ATENCAO: o modelo Whisper sera baixado no primeiro uso se nao estiver no cache.
echo Instale FFmpeg e yt-dlp via PREPARAR_FERRAMENTAS_WINDOWS.bat
pause
