$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$publish=Join-Path $root 'public'
New-Item -ItemType Directory -Force -Path $publish | Out-Null
$utf8=[Text.UTF8Encoding]::new($false)
$html=[IO.File]::ReadAllText((Join-Path $root 'index.html'))
$assets=@([regex]::Matches($html,'(?:src|href)="([a-zA-Z0-9_.-]+\.(?:js|css))(?=[?"])') | ForEach-Object {$_.Groups[1].Value} | Sort-Object -Unique)
foreach($item in ($assets + 'songbook_pages_204.js' + 'cloud-preview.js')){
  Copy-Item -LiteralPath (Join-Path $root $item) -Destination (Join-Path $publish $item) -Force
}
$html=$html.Replace('</body>','<script src="cloud-preview.js?v=1"></script></body>')
[IO.File]::WriteAllText((Join-Path $publish 'index.html'),$html,$utf8)