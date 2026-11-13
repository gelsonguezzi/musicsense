MUSICSENSE AI - STUDIO 0.4 (13/11/2026)
=====================================
Abra INICIAR_WINDOWS.bat ou http://localhost:8765 com o servidor ativo.
Pressione Ctrl+F5 após atualizar.

NOVO:
- Interface responsiva redesenhada e testada com Chrome headless em 1440 e 500 px.
- MP3, WAV, MP4, WMA, M4A, FLAC e OGG via análise local (compatibilidade depende dos codecs instalados).
- Vídeo local MP4 atrás das legendas, com duplo clique para tela cheia.
- YouTube com vídeo original se a incorporação for permitida. Em vídeos bloqueados, use Áudio + tradução.
- Grade de links usados/favoritos (armazenamento local do navegador). Duplo clique carrega e inicia a análise.
- PDF: pré-visualização no navegador, impressão e Salvar como PDF, original ou original + tradução.
- Acordes opcionais informados manualmente, com transposição do tom original para o desejado.
- Exportação MP4 vertical 4:5, 720x900, com legendas em inglês/português embutidas, para ARQUIVOS LOCAIS autorizados.
- Controles de próximo trecho, repetir trecho, bolinha e legendas.

LIMITES IMPORTANTES:
- A tradução portuguesa destaca progressivamente de forma proporcional aos tempos em inglês; não é alinhamento semântico palavra por palavra.
- O YouTube pode impedir incorporação, downloads ou análise. Não contornamos bloqueios de incorporação.
- Exportação de vídeo para compartilhamento é destinada a arquivos para os quais você possui direitos/autorização. Não exporta automaticamente vídeos de terceiros do YouTube.
- Acordes são fornecidos pelo usuário: o sistema NÃO extrai partitura ou notas musicais da gravação.
- Formato 'ST3' precisa ser identificado (extensão e exemplo) antes de ser implementado; não está anunciado como suportado.
- PDF é salvo pelo diálogo de impressão do navegador: escolha 'Salvar como PDF'.
- O servidor local só está acessível no computador; uso no iPhone requer hospedagem ou acesso seguro à rede.
- O modelo Whisper pode cometer erros em músicas com instrumentos altos, coros e sobreposição de vozes.

TESTES TÉCNICOS:
- Sintaxe JS dos 4 módulos: OK.
- Sintaxe Python: OK.
- HTTP da página: 200.
- Exportação WAV->MP4: OK.
- Exportação MP4->MP4: OK (720x900, duração 2s).
- Capturas de desktop e mobile guardadas em _qa_studio.
- Não há confirmação ainda de todos os fluxos clicados manualmente por usuário real.

BACKUP:
index_backup_before_studio2.html
server_backup_before_studio2.py
youtube_ui_backup_before_studio2.js

[executed on device: ESCRITORIO (015f09d9-8ae6-4cef-a39b-c7592204d204)]
