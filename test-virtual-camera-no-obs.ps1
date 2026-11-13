param([string]$Word)
$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
$python=Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if ($Word) { & $python 'training/no_obs_virtual_camera.py' '--word' $Word }
else { & $python 'training/no_obs_virtual_camera.py' }
if ($LASTEXITCODE -ne 0) { throw 'Fake-camera launcher failed. See the error above.' }
