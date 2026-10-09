$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
$sourceUrl = 'https://codeload.github.com/Azizbek-dsgn/UzScribe/zip/refs/heads/main'
$work = Join-Path ([IO.Path]::GetTempPath()) ('uzscribe-' + [guid]::NewGuid().ToString('N'))
$logRoot = Join-Path $env:LOCALAPPDATA 'UzbekSubtitles'
$logPath = Join-Path $logRoot 'install.log'
$previousUvInstall = $env:UV_UNMANAGED_INSTALL
$previousUzscribeUv = $env:UZSCRIBE_UV_BIN
$previousPythonUtf8 = $env:PYTHONUTF8
$previousPythonEncoding = $env:PYTHONIOENCODING
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
try { [Console]::OutputEncoding = [Text.UTF8Encoding]::new($false) } catch {}
$OutputEncoding = [Text.UTF8Encoding]::new($false)
$transcriptStarted = $false
try {
  # Small bootstrap reserve; Python checks the complete missing-model budget.
  foreach ($checkPath in @($logRoot, $work)) {
    $drive = [IO.DriveInfo]::new([IO.Path]::GetPathRoot([IO.Path]::GetFullPath($checkPath)))
    if ($drive.AvailableFreeSpace -lt 1GB) {
      throw "$($drive.Name) diskda joy yetarli emas. Avval kamida 1 GiB joy bo'shating; keyingi tekshiruv barcha modellar uchun kerakli joyni ko'rsatadi."
    }
  }
  New-Item -ItemType Directory -Path $work | Out-Null
  New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
  try {
    Start-Transcript -Path $logPath -Append -ErrorAction Stop | Out-Null
    $transcriptStarted = $true
  } catch {
    Write-Warning "O'rnatish jurnalini yozib bo'lmadi: $($_.Exception.Message)"
  }
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
    $powerShellExecutable = (Get-Process -Id $PID).Path
    & $powerShellExecutable -NoProfile -ExecutionPolicy Bypass -File $uvScript
    if ($LASTEXITCODE -ne 0) { throw "uv o'rnatilmadi (kod $LASTEXITCODE)." }
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
  $bundledModel = Join-Path $source.FullName 'models/large-v3'
  if (Test-Path (Join-Path $bundledModel 'model.bin')) {
    $installArgs += @('--model-dir', $bundledModel)
  }
  & $python @installArgs
  if ($LASTEXITCODE -eq 28) { throw "Diskda joy yetarli emas. Joy bo'shatib, shu buyruqni qayta bajaring; yuklangan modellar saqlanadi." }
  if ($LASTEXITCODE -ne 0) { throw 'UzScribe install failed.' }
  Write-Host "UzScribe o'rnatildi. Jurnal: $logPath"
} catch {
  Write-Host "UzScribe o'rnatilmadi: $($_.Exception.Message)" -ForegroundColor Red
  Write-Host "Xato jurnali: $logPath"
  throw
} finally {
  if ($transcriptStarted) { Stop-Transcript | Out-Null }
  $env:UV_UNMANAGED_INSTALL = $previousUvInstall
  $env:UZSCRIBE_UV_BIN = $previousUzscribeUv
  $env:PYTHONUTF8 = $previousPythonUtf8
  $env:PYTHONIOENCODING = $previousPythonEncoding
  Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
}
