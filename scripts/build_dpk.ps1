# Build script for Alluci DPK Kernel on Windows
# Requires Microsoft Visual C++ (MSVC) build tools

$sourceFile = "backend\security\dpk_kernel.cpp"
$outputFile = "backend\security\libdpk.dll"

Write-Host "Checking for MSVC compiler (cl.exe)..." -ForegroundColor Cyan
if (!(Get-Command cl -ErrorAction SilentlyContinue)) {
    Write-Error "cl.exe not found. Please run this from a Developer PowerShell for VS or ensure MSVC is in your PATH."
    exit 1
}

Write-Host "Building $outputFile from $sourceFile..." -ForegroundColor Cyan
cl.exe /O2 /LD /Fe:$outputFile $sourceFile /EHsc

if ($LASTEXITCODE -eq 0) {
    Write-Host "Build successful: $outputFile" -ForegroundColor Green
    # Cleanup temporary files
    Get-ChildItem -Path "backend\security\" -Include "*.obj","*.exp","*.lib" -Recurse | Remove-Item
} else {
    Write-Error "Build failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}
