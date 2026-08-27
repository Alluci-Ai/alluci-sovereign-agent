import pytest
import os
import tempfile
from backend.engine.code_health_detector import CodeHealthDetector

@pytest.mark.asyncio
async def test_code_health_detector_scan():
    with tempfile.TemporaryDirectory() as tmpdir:
        backend_dir = os.path.join(tmpdir, "backend")
        os.makedirs(backend_dir, exist_ok=True)

        # Create a sample python file with high complexity
        sample_file = os.path.join(backend_dir, "complex_service.py")
        long_body = "\n".join([f"    x_{i} = {i} * 2" for i in range(50)])
        with open(sample_file, "w", encoding="utf-8") as f:
            f.write(f"def huge_monolithic_function():\n{long_body}\n    return x_49\n")

        detector = CodeHealthDetector(project_root=tmpdir)
        findings = detector._scan_python_files(max_files=10)
        assert len(findings) > 0
        assert findings[0]["issue_type"] == "HIGH_CYCLOMATIC_COMPLEXITY"
        assert findings[0]["function"] == "huge_monolithic_function"

        opp = await detector.detect(world=None)
        assert opp is not None
        assert opp.detector_name == "CodeHealthDetector"
        assert "huge_monolithic_function" in opp.description
