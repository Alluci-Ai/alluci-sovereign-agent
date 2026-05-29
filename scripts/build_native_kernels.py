#!/usr/bin/env python3
"""
Build script for all C++ native kernels in the Sovereign Agent.
Finds all .cpp files in specified directories and compiles them into
their respective local build/ directories.
"""
import os
import sys
import platform
import subprocess
import argparse
import shutil
import glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET_DIRS = [
    os.path.join(ROOT, "backend", "ace"),
    os.path.join(ROOT, "backend", "inference"),
    os.path.join(ROOT, "backend", "security"),
]

def get_binary_name(cpp_file: str) -> str:
    base = os.path.splitext(os.path.basename(cpp_file))[0]
    # For dpk_kernel.cpp, we maintain the legacy libdpk.so name for compatibility
    if base == "dpk_kernel":
        base_name = "dpk"
    else:
        base_name = base
        
    system = platform.system()
    if system == "Darwin":
        return f"lib{base_name}.dylib"
    elif system == "Linux":
        return f"lib{base_name}.so"
    elif system == "Windows":
        return f"{base_name}.dll"
    else:
        raise RuntimeError(f"Unsupported platform: {system}")

def get_binary_path(cpp_file: str) -> str:
    dir_path = os.path.dirname(cpp_file)
    build_dir = os.path.join(dir_path, "build")
    return os.path.join(build_dir, get_binary_name(cpp_file))

def binary_exists(cpp_file: str) -> bool:
    return os.path.isfile(get_binary_path(cpp_file))

def build_file(cpp_file: str) -> bool:
    system = platform.system()
    dir_path = os.path.dirname(cpp_file)
    build_dir = os.path.join(dir_path, "build")
    os.makedirs(build_dir, exist_ok=True)

    out = get_binary_path(cpp_file)

    if system == "Darwin":
        cmd = ["g++", "-O2", "-std=c++17", "-fPIC", "-Wall",
               "-dynamiclib", "-o", out, cpp_file]
    elif system == "Linux":
        cmd = ["g++", "-O2", "-std=c++17", "-fPIC", "-Wall",
               "-shared", "-o", out, cpp_file]
    elif system == "Windows":
        if shutil.which("cl"):
            cmd = ["cl", "/O2", "/EHsc", "/LD", f"/Fe:{out}", cpp_file]
        elif shutil.which("g++"):
            cmd = ["g++", "-O2", "-std=c++17", "-Wall",
                   "-shared", "-o", out, cpp_file]
        else:
            print("[KERNEL BUILD] No C++ compiler found on Windows.", file=sys.stderr)
            return False
    else:
        print(f"[KERNEL BUILD] Unsupported platform: {system}", file=sys.stderr)
        return False

    print(f"[KERNEL BUILD] Building {os.path.basename(cpp_file)} for {system}...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"[KERNEL BUILD] Build FAILED for {cpp_file}:\n{result.stderr}", file=sys.stderr)
        return False

    print(f"[KERNEL BUILD] ✅ Built: {out}")
    return True

def main():
    parser = argparse.ArgumentParser(description="Build Native Kernels")
    parser.add_argument("--force", action="store_true", help="Rebuild even if binary exists")
    parser.add_argument("--check", action="store_true", help="Only check binaries exist")
    args = parser.parse_args()

    cpp_files = []
    for d in TARGET_DIRS:
        cpp_files.extend(glob.glob(os.path.join(d, "*.cpp")))

    if not cpp_files:
        print("[KERNEL BUILD] No .cpp files found.")
        sys.exit(0)

    all_success = True
    for f in cpp_files:
        if args.check:
            if not binary_exists(f):
                print(f"[KERNEL BUILD] ❌ Kernel binary NOT found for {f}")
                all_success = False
            continue

        if binary_exists(f) and not args.force:
            print(f"[KERNEL BUILD] Binary already present for {os.path.basename(f)}. Use --force to rebuild.")
            continue

        if not build_file(f):
            all_success = False

    if args.check and all_success:
        print("[KERNEL BUILD] ✅ All kernel binaries present.")

    sys.exit(0 if all_success else 1)

if __name__ == "__main__":
    main()
