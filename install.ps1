# Alluci Sovereign Agent - Windows Installer
# Run with: powershell.exe -ExecutionPolicy Bypass -File install.ps1

Write-Host "--- Initializing Alluci Sovereign Architecture Setup (Windows) ---" -ForegroundColor Cyan

# 1. Check Admin Privileges
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Warning "Administrative privileges required for service installation. Please re-run as Administrator."
    # Non-blocking for now, just service install will fail
}

# 2. Check Python
$pythonVersion = & python --version 2>$null
if ($null -eq $pythonVersion) {
    Write-Host "[ INFO ]: Python not found. Installing via winget..."
    winget install -e --id Python.Python.3.11
} else {
    Write-Host "[ OK ]: $pythonVersion detected."
}

# 3. Install Ollama
$ollamaCheck = & ollama --version 2>$null
if ($null -eq $ollamaCheck) {
    Write-Host "[ INFO ]: Ollama not found. Installing via winget..."
    winget install -e --id Ollama.Ollama
} else {
    Write-Host "[ OK ]: Ollama detected."
}

# 4. Install Dependencies
Write-Host "[ INFO ]: Installing Python dependencies..."
pip install -r requirements.txt
pip install pywin32 win10toast-click keyring --break-system-packages # Standardizing deps

# 5. Initialize .env
if (-not (Test-Path ".env")) {
    Write-Host "[ INFO ]: Creating .env from template..."
    $key = [Guid]::NewGuid().ToString().Replace("-", "")
    $jwt = [Guid]::NewGuid().ToString().Replace("-", "")
    @"
APP_ENV=production
POLYTOPE_MASTER_KEY=$key
JWT_SECRET_KEY=$jwt
OLLAMA_URL=http://localhost:11434
"@ | Out-File -Encoding UTF8 .env
}

# 6. Compile Security Kernels (C++)
Write-Host "[ INFO ]: Compiling Alluci C++ Security Kernels..."
if (Test-Path "backend\core") {
    mkdir -Force build
    cd build
    cmake .. -G "Visual Studio 17 2022" -A x64
    cmake --build . --config Release
    cd ..
    Write-Host "[ OK ]: C++ Kernels compiled."
} else {
    Write-Warning "[ WARN ]: C++ core directory not found. Pure Python mode will be used."
}

# 7. Download Default Models
Write-Host "[ INFO ]: Scanning hardware and downloading default models..."
python scripts\download_models.py

# 8. Service Pre-check
Write-Host "[ INFO ]: Setup Complete."
Write-Host "[ ACTION ]: You can now run the agent via 'python backend/app.py' or through the UI Platform Dashboard."
