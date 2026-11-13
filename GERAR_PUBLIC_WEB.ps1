$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$publish = Join-Path $root 'public'
New-Item -ItemType Directory -Force -Path $publish | Out-Null
$assets = @('index.html','core2.js','youtube2.js','extras2.js','export2.js','studio2.css','cloud-preview.js','mobile_fit_051.css')
foreach ($asset in $assets) {
  $from = Join-Path $root $asset
  if (-not (Test-Path -LiteralPath $from)) { throw "Arquivo ausente: $asset" }
  Copy-Item -LiteralPath $from -Destination (Join-Path $publish $asset) -Force
}
$indexPath = Join-Path $publish 'index.html'
$html = [System.IO.File]::ReadAllText($indexPath)
if (-not $html.Contains('mobile_fit_051.css')) {
  $html = $html.Replace('</head>', '<link rel="stylesheet" href="mobile_fit_051.css?v=051"></head>')
}
if (-not $html.Contains('cloud-preview.js')) {
  $html = $html.Replace('</body></html>', '<script src="cloud-preview.js?v=1"></script></body></html>')
}
[System.IO.File]::WriteAllText($indexPath, $html, [System.Text.UTF8Encoding]::new($false))
$cssPath = Join-Path $publish 'studio2.css'
$css = [System.IO.File]::ReadAllText($cssPath)
$css += [Environment]::NewLine + '#cloudNotice{display:flex;flex-direction:column;gap:7px;border:1px solid #9775d8;background:#251a36;padding:15px 18px;border-radius:12px;margin:0 0 18px;font-size:13px;color:#e8ddf6}#cloudNotice span{color:#c6bad5;line-height:1.5}button:disabled{cursor:not-allowed;opacity:.5}' + [Environment]::NewLine
[System.IO.File]::WriteAllText($cssPath, $css, [System.Text.UTF8Encoding]::new($false))
Write-Output "Pasta publica atualizada: $publish"

[executed on device: ESCRITORIO (015f09d9-8ae6-4cef-a39b-c7592204d204)]
