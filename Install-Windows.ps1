$ErrorActionPreference = 'Stop'
$previousSource = $env:UZSCRIBE_SOURCE_DIR
try {
  $env:UZSCRIBE_SOURCE_DIR = $PSScriptRoot
  & (Join-Path $PSScriptRoot 'bootstrap-windows.ps1')
} finally {
  $env:UZSCRIBE_SOURCE_DIR = $previousSource
}
