$ErrorActionPreference = "Stop"

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $projectRoot

$arguments = @(
    "-m", "PyInstaller",
    "--clean",
    "--noconfirm",
    "--onefile",
    "--windowed",
    "--name", "BonaBot",
    "--paths", "src",
    "scripts\entrypoint.py"
)

& python @arguments
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Output "Built $projectRoot\dist\BonaBot.exe"
