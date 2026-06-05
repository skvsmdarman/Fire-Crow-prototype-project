$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
  throw "Python virtual environment was not found at $python"
}

Push-Location $root
try {
  & $python "scripts/validate.py" @args
}
finally {
  Pop-Location
}
