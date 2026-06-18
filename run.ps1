# BONK Blueprint Scanner - MONTHLY recorder (PowerShell alternative to run.bat).
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$stamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
Add-Content -LiteralPath "blueprint.log" -Value "==== $stamp ====" -Encoding utf8
$out = & $py bonk_blueprint_scanner.py --me 10 2>&1 | Out-String
Add-Content -LiteralPath "blueprint.log" -Value $out -Encoding utf8
if ($LASTEXITCODE -ne 0) {
  Add-Content -LiteralPath "blueprint.log" -Value "SCANNER FAILED (exit $LASTEXITCODE), skipping publish" -Encoding utf8
  exit 1
}
$pub = & cmd /c "`"$PSScriptRoot\publish.bat`"" 2>&1 | Out-String
Add-Content -LiteralPath "blueprint.log" -Value $pub -Encoding utf8
