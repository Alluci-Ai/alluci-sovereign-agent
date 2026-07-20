import argparse
import subprocess
import time
import os
import signal
import sys
import psutil

def get_process_memory(proc):
    try:
        process = psutil.Process(proc.pid)
        # Calculate RSS in GB
        rss_bytes = process.memory_info().rss
        for child in process.children(recursive=True):
            rss_bytes += child.memory_info().rss
        return rss_bytes / (1024 ** 3)
    except psutil.NoSuchProcess:
        return 0

def run_with_sentinel(target_script, max_memory_gb):
    print(f"==================================================")
    print(f"[SENTINEL] Starting {target_script}")
    print(f"[SENTINEL] Maximum Working Memory Limit: {max_memory_gb} GB")
    print(f"==================================================")
    
    while True:
        # Launch the target script
        proc = subprocess.Popen([sys.executable, target_script])
        
        try:
            while True:
                time.sleep(2)
                
                # Check if process terminated on its own
                if proc.poll() is not None:
                    print(f"\n[SENTINEL] Process finished naturally with exit code {proc.returncode}.")
                    return proc.returncode
                    
                # Monitor memory
                current_mem_gb = get_process_memory(proc)
                print(f"[SENTINEL] {target_script} memory usage: {current_mem_gb:.2f} GB", end="\r")
                
                if current_mem_gb > max_memory_gb:
                    print(f"\n[SENTINEL ALERT] Memory spike detected! ({current_mem_gb:.2f} GB > {max_memory_gb} GB)")
                    print(f"[SENTINEL] Gracefully terminating process {proc.pid}...")
                    
                    # Terminate tree
                    try:
                        parent = psutil.Process(proc.pid)
                        for child in parent.children(recursive=True):
                            child.terminate()
                        parent.terminate()
                        parent.wait(timeout=5)
                    except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                        proc.kill()
                    
                    print(f"[SENTINEL] Memory cleared. Restarting the process in 5 seconds to resume the sprint...")
                    time.sleep(5)
                    break # Break out of inner loop to restart the script
                    
        except KeyboardInterrupt:
            print("\n[SENTINEL] Keyboard interrupt received. Shutting down target process...")
            proc.terminate()
            proc.wait()
            print("[SENTINEL] Exiting.")
            sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Memory Sentinel Wrapper")
    parser.add_argument("--target", required=True, help="Path to the Python script to run")
    parser.add_argument("--max-memory-gb", type=float, default=12.0, help="Maximum allowed memory in GB")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.target):
        print(f"Error: Target script {args.target} not found.")
        sys.exit(1)
        
    run_with_sentinel(args.target, args.max_memory_gb)
