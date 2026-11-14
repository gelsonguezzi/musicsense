@echo off
setlocal
title MusicSense AI - Ferramentas
echo Instale Node.js 24 LTS, Python 3.11 ou 3.12 e FFmpeg se necessario.
where winget >nul 2>&1 || (echo Winget indisponivel. Instale os programas manualmente. & pause & exit /b 1)
winget install --id OpenJS.NodeJS.LTS -e --accept-package-agreements --accept-source-agreements
winget install --id Gyan.FFmpeg -e --accept-package-agreements --accept-source-agreements
winget install --id yt-dlp.yt-dlp -e --accept-package-agreements --accept-source-agreements
echo Feche e abra novamente o terminal para atualizar PATH.
pause
