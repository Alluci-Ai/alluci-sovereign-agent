import pytest
from unittest.mock import patch
from backend.security.vault import Sandbox

def test_sandbox_preexec_fn():
    sb = Sandbox("/tmp", {})
    with patch("subprocess.run") as mock_run:
        sb.run_command(["ls"])
        kwargs = mock_run.call_args[1]
        preexec_fn = kwargs.get("preexec_fn")
        if preexec_fn:
            with patch("os.setpgrp"), patch("os.setuid", create=True), patch("os.setgid", create=True):
                preexec_fn()
