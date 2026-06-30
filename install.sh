#!/usr/bin/env bash
# Alluci Sovereign Agent - macOS/Linux Installer

echo "--- Initializing Alluci Sovereign Architecture Setup (macOS/Linux) ---"

# 1. Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ INFO ]: Python3 not found. Please install python3."
    exit 1
else
    echo "[ OK ]: $(python3 --version) detected."
fi

# 2. Install Dependencies
echo "[ INFO ]: Installing Python dependencies..."
python3 -m pip install -r requirements.txt

# 3. Initialize .env
if [ ! -f ".env" ]; then
    echo "[ INFO ]: Creating .env from template..."
    key=$(uuidgen | tr -d '-')
    jwt=$(uuidgen | tr -d '-')
    cat <<EOF > .env
APP_ENV=production
POLYTOPE_MASTER_KEY=$key
JWT_SECRET_KEY=$jwt
OLLAMA_URL=http://localhost:11434
EOF
fi

# 4. Compile Security Kernels (C++)
echo "[ INFO ]: Compiling Alluci C++ Security Kernels..."
if [ -d "backend/core" ]; then
    mkdir -p build
    cd build
    cmake .. -DCMAKE_BUILD_TYPE=Release
    make -j$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)
    cd ..
    echo "[ OK ]: C++ Kernels compiled."
else
    echo "[ WARN ]: C++ core directory not found. Pure Python mode will be used."
fi

# 5. Download Default Models
echo "[ INFO ]: Scanning hardware and downloading default models..."
python3 scripts/download_models.py

echo "[ INFO ]: Setup Complete."
echo "[ ACTION ]: You can now run the agent via 'python3 backend/app.py' or through the UI Platform Dashboard."
