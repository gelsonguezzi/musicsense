@echo off
cd /d "%~dp0"
echo MusicSense AI - instalacao local gratuita
where py >nul 2>&1
if errorlevel 1 (echo Instale Python 3.11 ou 3.12 em python.org e execute novamente. & pause & exit /b 1)
py -3 -m venv .venv
if errorlevel 1 (echo Falha ao criar ambiente Python. & pause & exit /b 1)
call .venv\Scripts\python.exe -m pip install --upgrade pip
call .venv\Scripts\python.exe -m pip install faster-whisper argostranslate
if errorlevel 1 (echo Falha na instalacao. & pause & exit /b 1)
echo Instalando pacote de traducao ingles-portugues...
call .venv\Scripts\python.exe instalar_traducao.py
pause