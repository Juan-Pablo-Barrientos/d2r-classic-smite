# Builds dist\ClassicSmite.zip with the ClassicSmite mod folder at the top.
$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$dist = Join-Path $root "dist"
Remove-Item -Recurse -Force $dist -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $dist | Out-Null
Compress-Archive -Path "$root\ClassicSmite" -DestinationPath "$dist\ClassicSmite.zip"
Write-Host "Built $dist\ClassicSmite.zip"
