param([ValidateSet('sqlite','falkordb')][string]$Backend = 'sqlite')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$pythonPath = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create Python environment' }
}
& $pythonPath -c "import fastapi, uvicorn, httpx, mcp, numpy, pytest, matplotlib; from importlib.metadata import version; assert version('mnemograph') == '0.3.0'" 2>$null
if ($LASTEXITCODE -ne 0) {
    & $pythonPath -m pip install -e '.[dev]'
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
}
if ($Backend -eq 'falkordb') {
    & $pythonPath -m pip install -e '.[falkordb]'
    if ($LASTEXITCODE -ne 0) { throw 'FalkorDB adapter installation failed' }
}
& $pythonPath -m mnemograph serve --backend $Backend
