$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$python = $null
foreach ($version in @('-3.12', '-3.11', '-3.10')) {
  try {
    & py $version -c "import sys; assert (3,10) <= sys.version_info[:2] < (3,13)" 2>$null
    if ($LASTEXITCODE -eq 0) { $python = $version; break }
  } catch {}
}
if (-not $python) { throw 'Python 3.10–3.12 kerak: https://www.python.org/downloads/' }
if (Test-Path 'UzbekSubtitles.zxp') {
  & py $python install.py
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  Write-Host 'Endi UzbekSubtitles.zxp faylini Adobe orqali ornating.'
} else {
  & py $python install.py --developer
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
