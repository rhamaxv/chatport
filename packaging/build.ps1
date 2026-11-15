# Windows: PyInstaller bundle, then Inno Setup produces dist\Chatport-<version>-Setup.exe.
# Usage: pwsh packaging\build.ps1   ($env:PYTHON to pick an interpreter)
$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root
$Python = if ($env:PYTHON) { $env:PYTHON } else { "python" }

$Version = & $Python -c "import tomllib,pathlib;print(tomllib.loads(pathlib.Path('pyproject.toml').read_text(encoding='utf-8'))['project']['version'])"
if ($LASTEXITCODE -ne 0) { throw "could not read version from pyproject.toml" }
Write-Host "Building Chatport $Version for Windows"

& $Python packaging\make_icons.py
if ($LASTEXITCODE -ne 0) { throw "make_icons.py failed" }

& $Python -m PyInstaller --noconfirm --clean packaging\chatport.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }
if (-not (Test-Path "dist\Chatport\Chatport.exe")) { throw "missing dist\Chatport\Chatport.exe" }

$Iscc = (Get-Command iscc -ErrorAction SilentlyContinue).Source
if (-not $Iscc) {
    $Candidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
        "${env:LOCALAPPDATA}\Programs\Inno Setup 6\ISCC.exe"
    )
    $Iscc = $Candidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
}
if (-not $Iscc) { throw "Inno Setup (iscc) not found. Install it or add ISCC.exe to PATH." }

& $Iscc "/DAppVersion=$Version" packaging\installer.iss
if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed" }

Write-Host "Wrote dist\Chatport-$Version-Setup.exe"
