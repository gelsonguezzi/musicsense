MusicSense AI STABLE 205 - Windows

1. Execute PREPARAR_FERRAMENTAS_WINDOWS.bat como administrador se necessario.
2. Execute INSTALAR_WINDOWS.bat.
3. Execute INICIAR_WINDOWS.bat.
4. Acesse http://127.0.0.1:8765.
5. ATUALIZAR_WINDOWS.bat atualiza bibliotecas Python.

ATENCAO: youtube_support.py atualmente usa caminhos fixos C:\Yt-dlp para yt-dlp e FFmpeg. Em outro PC, configure C:\Yt-dlp ou ajuste os caminhos no codigo. O instalador winget instala no PATH, mas nao cria essa pasta. O modelo Whisper e pacotes Argos podem exigir downloads adicionais. Nao ha garantia de funcionamento offline imediato.

Netlify: apenas interface estatica. Transcricao e traducao exigem servidor Python local ou backend separado. Nao exponha a porta 8765 publicamente.

Backup do codigo fonte, nao inclui ambientes virtuais, cache, modelos, musicas nem credenciais.
