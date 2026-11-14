$root='C:\Users\GELTV\Desktop\Projetos de Paginas\Music Sense'
$port=Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue
if($port){try{$r=Invoke-WebRequest 'http://127.0.0.1:8765/api/health' -UseBasicParsing -TimeoutSec 3;if($r.StatusCode -eq 200){exit 0}}catch{}}
Start-Process -FilePath "$root\.venv\Scripts\python.exe" -ArgumentList '-u server.py' -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput "$root\musicsense_stdout.log" -RedirectStandardError "$root\musicsense_stderr.log"