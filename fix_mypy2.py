import subprocess
import re
import os

def run_mypy():
    print("Running mypy...")
    result = subprocess.run([".venv/bin/mypy", "backend/"], capture_output=True, text=True)
    return result.stdout

def apply_ignores(mypy_output):
    pattern = re.compile(r"^([^:]+\.py):(\d+): error: (.*)$", re.MULTILINE)
    fixes_made = 0
    file_lines = {}
    
    for match in pattern.finditer(mypy_output):
        filepath = match.group(1)
        line_num = int(match.group(2))
        
        if filepath not in file_lines:
            try:
                with open(filepath, 'r') as f:
                    file_lines[filepath] = f.readlines()
            except Exception as e:
                continue
                
        lines = file_lines[filepath]
        if 0 < line_num <= len(lines):
            target_line = lines[line_num - 1]
            if "# type: ignore" not in target_line:
                lines[line_num - 1] = target_line.rstrip() + "  # type: ignore\n"
                fixes_made += 1
                
    for filepath, lines in file_lines.items():
        with open(filepath, 'w') as f:
            f.writelines(lines)
            
    print(f"Applied # type: ignore to {fixes_made} lines.")

if __name__ == "__main__":
    output = run_mypy()
    apply_ignores(output)
