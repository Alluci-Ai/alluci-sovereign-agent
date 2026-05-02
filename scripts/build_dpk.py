#!/usr/bin/env python3
"""
Cross-platform DPK kernel build helper.
Detects platform, runs the appropriate compiler, and verifies the output.

Usage:
   python scripts/build_dpk.py           # Auto-detect platform
   python scripts/build_dpk.py --force   # Rebuild even if binary exists
   python scripts/build_dpk.py --check   # Only verify binary exists, exit 1 if not

Called by: pip install -e . post-install hook, CI, and setup_sovereign_stack.sh
"""
import os
import sys
import platform
import subprocess
import argparse
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECURITY_DIR = os.path.join(ROOT, "backend", "security")
BUILD_DIR = os.path.join(SECURITY_DIR, "build")


def get_binary_path() -> str:
   system = platform.system()
   if system == "Darwin":
       return os.path.join(BUILD_DIR, "libdpk.dylib")
   elif system == "Linux":
       return os.path.join(BUILD_DIR, "libdpk.so")
   elif system == "Windows":
       return os.path.join(BUILD_DIR, "dpk.dll")
   else:
       raise RuntimeError(f"Unsupported platform: {system}")


def binary_exists() -> bool:
   return os.path.isfile(get_binary_path())


def build() -> bool:
   system = platform.system()
   os.makedirs(BUILD_DIR, exist_ok=True)

   src = os.path.join(SECURITY_DIR, "dpk_kernel.cpp")
   out = get_binary_path()

   if system == "Darwin":
       cmd = ["g++", "-O2", "-std=c++17", "-fPIC", "-Wall",
              "-dynamiclib", "-o", out, src]
   elif system == "Linux":
       cmd = ["g++", "-O2", "-std=c++17", "-fPIC", "-Wall",
              "-shared", "-o", out, src]
   elif system == "Windows":
       # MSVC or MinGW
       if shutil.which("cl"):
           cmd = ["cl", "/O2", "/EHsc", "/LD", f"/Fe:{out}", src]
       elif shutil.which("g++"):
           cmd = ["g++", "-O2", "-std=c++17", "-Wall",
                  "-shared", "-o", out, src]
       else:
           print("[DPK BUILD] No C++ compiler found on Windows. "
                 "Install Visual Studio Build Tools or MinGW.", file=sys.stderr)
           return False
   else:
       print(f"[DPK BUILD] Unsupported platform: {system}", file=sys.stderr)
       return False

   print(f"[DPK BUILD] Building for {system}: {' '.join(cmd)}")
   result = subprocess.run(cmd, capture_output=True, text=True)

   if result.returncode != 0:
       print(f"[DPK BUILD] Build FAILED:\n{result.stderr}", file=sys.stderr)
       return False

   print(f"[DPK BUILD] ✅ Built: {out}")
   return True


def check() -> bool:
   if binary_exists():
       print(f"[DPK BUILD] ✅ Kernel binary present: {get_binary_path()}")
       return True
   else:
       print(f"[DPK BUILD] ❌ Kernel binary NOT found: {get_binary_path()}")
       return False


if __name__ == "__main__":
   parser = argparse.ArgumentParser(description="Build DPK Native Kernel")
   parser.add_argument("--force", action="store_true", help="Rebuild even if binary exists")
   parser.add_argument("--check", action="store_true", help="Only check binary exists")
   args = parser.parse_args()

   if args.check:
       sys.exit(0 if check() else 1)

   if binary_exists() and not args.force:
       print("[DPK BUILD] Kernel binary already present. Use --force to rebuild.")
       sys.exit(0)

   success = build()
   sys.exit(0 if success else 1)
