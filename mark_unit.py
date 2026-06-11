import os

tests_dir = "backend/tests"
exclude_dirs = ["integration"]
exclude_files = ["test_00_sanity.py", "conftest.py"]

for root, dirs, files in os.walk(tests_dir):
    # Skip excluded directories
    dirs[:] = [d for d in dirs if d not in exclude_dirs]
    
    for file in files:
        if file.startswith("test_") and file.endswith(".py") and file not in exclude_files:
            filepath = os.path.join(root, file)
            with open(filepath, "r") as f:
                content = f.read()
            
            if "pytestmark = pytest.mark.unit" not in content and "@pytest.mark.integration" not in content:
                # Add pytestmark at the top after imports
                # Let's just prepend it.
                if "import pytest" not in content:
                    new_content = "import pytest\npytestmark = pytest.mark.unit\n\n" + content
                else:
                    new_content = "import pytest\npytestmark = pytest.mark.unit\n\n" + content.replace("import pytest\n", "")
                
                with open(filepath, "w") as f:
                    f.write(new_content)
                print(f"Marked {filepath} as unit")
