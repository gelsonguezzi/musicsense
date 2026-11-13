# MusicSense AI

Aplicativo de música, transcrição em inglês e tradução para português com exibição sincronizada.

## Estado atual

- **Windows (local):** a interface conversa com o backend Python em `http://127.0.0.1:8765`, usando `faster-whisper` e `Argos Translate`.
- **Netlify (público):** demonstração da interface responsiva, reprodução local e player de vídeos que permitam incorporação. **A análise de música com IA ainda não está disponível no site público.**
- **Próxima fase:** desenvolver e conectar backend público de processamento de áudio com limites, autenticação, segurança, orçamento e regras de direitos autorais.

## Windows

1. Instale Python 3.12 x64.
2. Execute `INSTALAR_WINDOWS.bat` na pasta do projeto.
3. Execute `INICIAR_WINDOWS.bat` e abra `http://127.0.0.1:8765`.
4. No primeiro uso, haverá download dos modelos. O modo YouTube local usa os executáveis `C:\Yt-dlp\yt-dlp.exe` e `C:\Yt-dlp\ffmpeg.exe` quando instalados.

## Publicação Netlify

O conteúdo estático público fica em `public/`. O `netlify.toml` configura `publish = "public"`. O backend Python local não é publicado como função Netlify.

## Restrições

Reprodução de vídeos do YouTube pode ser bloqueada por seus titulares. Transcrições são aproximadas. Exportação de vídeos de terceiros exige autorização. Os acordes para PDF devem ser fornecidos pelo usuário.

Não incluir no GitHub: `.venv`, áudios pessoais, modelos, cache e credenciais.

[executed on device: ESCRITORIO (015f09d9-8ae6-4cef-a39b-c7592204d204)]
