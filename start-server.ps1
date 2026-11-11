# Use the project environment: the system Python may not have motion-model dependencies.
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    $python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    if (!(Test-Path -LiteralPath $python)) {
        throw 'The project Python environment is missing. Set up Python 3.11 and the training dependencies first.'
    }
    & $python -c 'import torch, mediapipe'
    if ($LASTEXITCODE -ne 0) { throw 'The project Python environment needs its motion-model dependencies repaired.' }
    & $python -u server.py
} finally {
    Pop-Location
}
