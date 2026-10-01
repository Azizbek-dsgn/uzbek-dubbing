$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
$sourceUrl = 'https://codeload.github.com/Azizbek-dsgn/uzbek-dubbing/zip/refs/heads/feat/uzbek-subtitles-adobe'
$work = Join-Path ([IO.Path]::GetTempPath()) ('uzscribe-' + [guid]::NewGuid().ToString('N'))
$previousUvInstall = $env:UV_UNMANAGED_INSTALL
$previousUzscribeUv = $env:UZSCRIBE_UV_BIN
New-Item -ItemType Directory -Path $work | Out-Null
try {
  if ($env:UZSCRIBE_SOURCE_DIR) {
    $source = Get-Item -LiteralPath $env:UZSCRIBE_SOURCE_DIR
  } else {
    $archive = Join-Path $work 'source.zip'
    if ($env:UZSCRIBE_ARCHIVE_PATH) {
      Copy-Item -LiteralPath $env:UZSCRIBE_ARCHIVE_PATH -Destination $archive
    } else {
      Invoke-WebRequest -Uri $sourceUrl -OutFile $archive -UseBasicParsing
    }
    $sourceParent = Join-Path $work 'source'
    Expand-Archive -LiteralPath $archive -DestinationPath $sourceParent
    $source = Get-ChildItem -LiteralPath $sourceParent -Directory | Select-Object -First 1
  }
  if (-not $source -or -not (Test-Path (Join-Path $source.FullName 'install_online.py'))) {
    throw 'UzScribe kodi topilmadi.'
  }

  if ($env:UZSCRIBE_UV_BIN -and (Test-Path -LiteralPath $env:UZSCRIBE_UV_BIN)) {
    $uv = $env:UZSCRIBE_UV_BIN
  } else {
    $uvScript = Join-Path $work 'uv-install.ps1'
    Invoke-WebRequest -Uri 'https://astral.sh/uv/install.ps1' -OutFile $uvScript -UseBasicParsing
    $env:UV_UNMANAGED_INSTALL = Join-Path $work 'uv-bin'
    Invoke-Expression (Get-Content -LiteralPath $uvScript -Raw)
    $uv = Join-Path $env:UV_UNMANAGED_INSTALL 'uv.exe'
    if (-not (Test-Path -LiteralPath $uv)) { throw 'uv.exe topilmadi.' }
    $env:UZSCRIBE_UV_BIN = $uv
  }

  $python = $null
  $forceManagedPython = $env:UZSCRIBE_FORCE_MANAGED_PYTHON -eq '1'
  if (-not $forceManagedPython -and (Get-Command py -ErrorAction SilentlyContinue)) {
    foreach ($version in @('-3.12', '-3.11', '-3.10')) {
      try {
        $candidate = (& py $version -c 'import sys; print(sys.executable)' 2>$null)
        if ($LASTEXITCODE -eq 0 -and $candidate) { $python = $candidate.Trim(); break }
      } catch {}
    }
  }
  if (-not $python -and -not $forceManagedPython) {
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
    & $uv python install 3.12
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 yuklanmadi.' }
    $foundPython = & $uv python find 3.12
    if ($LASTEXITCODE -ne 0 -or -not $foundPython) {
      throw 'Python 3.12 fayli topilmadi.'
    }
    $python = $foundPython.Trim()
    if (-not (Test-Path -LiteralPath $python)) {
      throw 'Python 3.12 fayli topilmadi.'
    }
  }

  $installArgs = @((Join-Path $source.FullName 'install_online.py'))
  $bundledModel = Join-Path $source.FullName 'models/navai-small'
  if (Test-Path (Join-Path $bundledModel 'model.bin')) {
    $installArgs += @('--model-dir', $bundledModel)
  }
  & $python @installArgs
  if ($LASTEXITCODE -ne 0) { throw 'UzScribe install failed.' }
} finally {
  $env:UV_UNMANAGED_INSTALL = $previousUvInstall
  $env:UZSCRIBE_UV_BIN = $previousUzscribeUv
  Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
}
