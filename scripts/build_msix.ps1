param(
    [string]$OutputDir = ".\dist_msix",
    [string]$OutputFile = "AlluciSovereignAgent.msix"
)
Set-StrictMode -Version Latest; $ErrorActionPreference = "Stop"

Write-Host "[ BUILD ] Compiling frontend..."
npm run build

Write-Host "[ STAGE ] Creating package layout..."
New-Item -ItemType Directory -Force -Path "$OutputDir\app" | Out-Null
Copy-Item -Recurse -Force ".\dist\*" "$OutputDir\app\frontend\"
Copy-Item -Recurse -Force ".\backend\" "$OutputDir\app\backend\"
Copy-Item -Force ".\Package.appxmanifest" "$OutputDir\"
New-Item -ItemType Directory -Force -Path "$OutputDir\public" | Out-Null
Copy-Item -Force ".\public\icon-192.png" "$OutputDir\public\"
Copy-Item -Force ".\public\icon-512.png" "$OutputDir\public\"

Write-Host "[ PACK ] Creating MSIX..."
makeappx pack /d "$OutputDir" /p "$OutputFile" /nv
Write-Host "[ DONE ] $OutputFile created."
Write-Host "[ NOTE ] Sign before distribution:"
Write-Host "         signtool sign /fd sha256 /a $OutputFile"
