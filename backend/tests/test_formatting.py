import os, glob, json, pytest
from backend.inference.router import ModelRouter
from unittest.mock import MagicMock

def test_core_skills_arrows():
    core_skills_dir = os.path.join(os.getcwd(), "core_skills")
    json_files = glob.glob(os.path.join(core_skills_dir, "*.json"))
    assert len(json_files) > 0, "No skill files found in core_skills/"
    
    for filepath in json_files:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        assert "->" not in content, f"File {os.path.basename(filepath)} still contains raw ASCII arrow '->'"

def test_sanitize_formatting():
    router = ModelRouter(settings=MagicMock(), vault=MagicMock())
    
    raw1 = "Understand Client Objectives $\\rightarrow$ Define Value Creation"
    clean1 = router._sanitize_formatting(raw1)
    assert clean1 == "Understand Client Objectives → Define Value Creation"
    
    raw2 = "Step 1 \\rightarrow Step 2"
    clean2 = router._sanitize_formatting(raw2)
    assert clean2 == "Step 1 → Step 2"
