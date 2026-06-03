#!/bin/bash
set -e

echo "=============================================="
echo "    Polytope Sovereign Agent - Build & Sign   "
echo "=============================================="

# Check for macOS
if [ "$(uname)" != "Darwin" ]; then
    echo "Error: This build script is currently only supported on macOS."
    exit 1
fi

APP_NAME="AlluciSovereign"
DIST_DIR="dist/$APP_NAME.app"
IDENTITY="Alluci Fulcanelli" # Self-signed testing certificate

echo "[1/4] Cleaning previous builds..."
rm -rf build dist

echo "[2/4] Building standalone binary with PyInstaller..."
# We assume PyInstaller is installed in the current environment
pyinstaller --name "$APP_NAME" \
            --windowed \
            --noconfirm \
            --clean \
            backend/engine/executor.py # or whichever entry point

echo "[3/4] Securing binary with Hardened Runtime Entitlements..."
cat << 'EOF' > entitlements.plist
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.cs.allow-jit</key>
    <true/>
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
    <key>com.apple.security.network.client</key>
    <true/>
    <key>com.apple.security.network.server</key>
    <true/>
</dict>
</plist>
EOF

echo "[4/4] Signing application with identity: $IDENTITY..."
codesign --force --options runtime --entitlements entitlements.plist --sign "$IDENTITY" --deep "$DIST_DIR"

echo "=============================================="
echo "✅ Build & Code Signing Complete!"
echo "You can verify the signature with: codesign -dv --verbose=4 $DIST_DIR"
echo "Note: altool notarization requires a paid Apple Developer ID."
echo "=============================================="
