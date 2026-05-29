#!/usr/bin/env python3
"""
Legacy DPK kernel build helper.
Shimmed to call scripts/build_native_kernels.py for backward compatibility.
"""
import os
import sys
import subprocess

if __name__ == "__main__":
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    script = os.path.join(root, "scripts", "build_native_kernels.py")
    result = subprocess.run([sys.executable, script] + sys.argv[1:])
    sys.exit(result.returncode)
