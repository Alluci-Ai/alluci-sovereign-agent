import os
import sys
import subprocess
import platform

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_dir = os.path.join(base_dir, "backend", "security")
    src_file = os.path.join(target_dir, "dpk_kernel.cpp")
    
    if not os.path.exists(src_file):
        print(f"Error: Source file {src_file} not found.")
        sys.exit(1)
        
    system = platform.system()
    
    # Common flags for C++ compilation
    compiler = os.environ.get("CXX", "g++" if system != "Darwin" else "clang++")
    flags = ["-O3", "-std=c++11"]
    
    # Platform-specific flags and extensions
    if system == "Darwin":
        ext = ".dylib"
        flags.extend(["-shared", "-fPIC"])
    elif system == "Linux":
        ext = ".so"
        flags.extend(["-shared", "-fPIC"])
    elif system == "Windows":
        ext = ".dll"
        # Windows MSVC compiler uses different flags.
        # This basic script assumes cl.exe if on Windows and no alternative compiler is specified.
        # A more robust script would use setuptools/CMAKE.
        compiler = "cl"
        flags = ["/O2", "/LD"]
    else:
        print(f"Unsupported system: {system}")
        sys.exit(1)
        
    out_file = os.path.join(target_dir, f"libdpk{ext}")
    
    if compiler == "cl":
        cmd = [compiler] + flags + [src_file, f"/Fe:{out_file}"]
    else:
        cmd = [compiler] + flags + [src_file, "-o", out_file]
        
    print(f"Building DPK kernel native extension...")
    print(f"Running: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
        print(f"Successfully built {out_file}")
    except subprocess.CalledProcessError as e:
        print(f"Build failed with error code: {e.returncode}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"Error: Compiler '{compiler}' not found. Please install build tools (e.g. clang, gcc, MSVC).")
        sys.exit(1)

if __name__ == "__main__":
    main()
