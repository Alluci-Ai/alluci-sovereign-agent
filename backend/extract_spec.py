import os
import re

spec_file = "Alluci_Production_Testing_Spec.md"

with open(spec_file, "r") as f:
    content = f.read()

# Pattern to find file name and code block
# e.g., **File:** `backend/pytest.ini` — **REPLACE**
# \n```ini\n <content> \n```

matches = re.finditer(r"\*\*File:\*\*\s+`([^`]+)`.*?\n\n.*?\s*```[a-z]*\n(.*?)```", content, re.DOTALL)

for match in matches:
    filename = match.group(1).strip()
    code = match.group(2)
    
    # ensure it's absolute or relative properly
    # The filenames usually start with backend/ or just are relative to root.
    # We are running from backend/, so if it starts with 'backend/', remove it to write correctly here?
    # Wait, vitest.config.ts is at root. 
    # Let's write them relative to the project root instead.
    root_path = os.path.join(os.path.dirname(__file__), "..", filename)
    root_path = os.path.abspath(root_path)

    os.makedirs(os.path.dirname(root_path), exist_ok=True)
    with open(root_path, "w") as out:
        out.write(code)
        
    print(f"Created/Replaced file: {root_path}")
