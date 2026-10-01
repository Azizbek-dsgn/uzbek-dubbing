$ErrorActionPreference = 'Stop'
$sourceUrl = 'https://codeload.github.com/Azizbek-dsgn/uzbek-dubbing/zip/refs/heads/feat/uzbek-subtitles-adobe'
$work = Join-Path ([IO.Path]::GetTempPath()) ('uzscribe-' + [guid]::NewGuid().ToString('N'))
$previousUvInstall = $env:UV_UNMANAGED_INSTALL
New-Item -ItemType Directory -Path $work | Out-Null
try {
  $archive = Join-Path $work 'source.zip'
  if ($env:UZSCRIBE_ARCHIVE_PATH) {
    Copy-Item -LiteralPath $env:UZSCRIBE_ARCHIVE_PATH -Destination $archive
  } else {
    Invoke-WebRequest -Uri $sourceUrl -OutFile $archive -UseBasicParsing
  }
  $sourceParent = Join-Path $work 'source'
  Expand-Archive -LiteralPath $archive -DestinationPath $sourceParent
  $source = Get-ChildItem -LiteralPath $sourceParent -Directory | Select-Object -First 1
  if (-not $source -or -not (Test-Path (Join-Path $source.FullName 'install_online.py'))) {
    throw 'UzScribe kodi topilmadi.'
  }

  $python = $null
  if (Get-Command py -ErrorAction SilentlyContinue) {
    foreach ($version in @('-3.12', '-3.11', '-3.10')) {
      try {
        $candidate = (& py $version -c 'import sys; print(sys.executable)' 2>$null)
        if ($LASTEXITCODE -eq 0 -and $candidate) { $python = $candidate.Trim(); break }
      } catch {}
    }
  }
  if (-not $python) {
    foreach ($candidate in @('python3', 'python')) {
      if (-not (Get-Command $candidate -ErrorAction SilentlyContinue)) { continue }
      try {
        $version = (& $candidate -c 'import sys; print(sys.version_info[:2])' 2>$null)
        if ($LASTEXITCODE -eq 0 -and $version -match '^\(3, (10|11|12)\)') {
          $python = (& $candidate -c 'import sys; print(sys.executable)').Trim()
          break
        }
      } catch {}
    }
  }
  if (-not $python) {
    Write-Host 'Python 3.12 tayyorlanmoqda...'
    $uvScript = Join-Path $work 'uv-install.ps1'
    Invoke-WebRequest -Uri 'https://astral.sh/uv/install.ps1' -OutFile $uvScript -UseBasicParsing
    $env:UV_UNMANAGED_INSTALL = Join-Path $work 'uv-bin'
    powershell -NoProfile -ExecutionPolicy Bypass -File $uvScript
    if ($LASTEXITCODE -ne 0) { throw 'Python o‘rnatuvchisi ishga tushmadi.' }
    $uv = Join-Path $env:UV_UNMANAGED_INSTALL 'uv.exe'
    & $uv python install 3.12
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 yuklanmadi.' }
    $python = (& $uv python find 3.12).Trim()
  }

  & $python (Join-Path $source.FullName 'install_online.py')
  if ($LASTEXITCODE -ne 0) { throw 'UzScribe o‘rnatilmadi.' }
} finally {
  $env:UV_UNMANAGED_INSTALL = $previousUvInstall
  Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
}
