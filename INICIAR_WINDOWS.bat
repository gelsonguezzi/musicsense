@echo off
setlocal
cd /d "%~dp0"
title MusicSense AI - Servidor local
echo ==========================================
echo          MusicSense AI - Windows
echo ==========================================
if not exist ".venv\Scripts\python.exe" (
  echo ERRO: Ambiente Python nao encontrado.
  echo Nao execute instalacoes sem verificar as dependencias.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -c "import av, faster_whisper, argostranslate; print('Dependencias OK - PyAV', av.__version__)"
if errorlevel 1 (
  echo ERRO: Dependencias incompletas. Nao foi possivel iniciar.
  pause
  exit /b 1
)
powershell -NoProfile -Command "try { $r=Invoke-RestMethod -Uri 'http://127.0.0.1:8765/api/health' -TimeoutSec 2; if($r.ok){exit 0}else{exit 1} } catch {exit 1}"
if not errorlevel 1 (
  echo Servidor ja esta funcionando. Abrindo navegador...
  start "" "http://127.0.0.1:8765"
  exit /b 0
)
echo Iniciando servidor corrigido...
start "" "http://127.0.0.1:8765"
".venv\Scripts\python.exe" -u "server.py"
echo.
echo Servidor encerrado. Confira as mensagens acima.
pause