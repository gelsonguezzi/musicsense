@echo off
setlocal
cd /d "%~dp0"
title MusicSense AI - Publicar Netlify
set "CLI=%APPDATA%\npm\netlify.cmd"
if not exist "%CLI%" (
  echo ERRO: Netlify CLI nao encontrado.
  echo Instale com npm install -g netlify-cli e faca login.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0GERAR_PUBLIC_WEB.ps1"
if errorlevel 1 (
  echo Erro ao preparar os arquivos estaticos.
  pause
  exit /b 1
)
call "%CLI%" deploy --site f1295961-329b-48ea-b3db-b0168e7b480a --prod --dir "%~dp0public" --no-build --message "MusicSense AI atualizacao web"
if errorlevel 1 (
  echo Falha no deploy. Nenhum outro site deve ser alterado.
  pause
  exit /b 1
)
echo.
echo Publicado em https://musicsense.netlify.app
pause

[executed on device: ESCRITORIO (015f09d9-8ae6-4cef-a39b-c7592204d204)]
