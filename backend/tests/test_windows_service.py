import pytest
import sys
import asyncio

# We no longer skip on non-Windows to ensure coverage runs everywhere.
# We mock all the windows specific modules below.

from unittest.mock import patch, MagicMock, AsyncMock

# Mock windows-specific modules globally so that any delayed imports succeed
mock_win32serviceutil = MagicMock()
class MockServiceFramework:
    def __init__(self, args):
        pass
    def ReportServiceStatus(self, status):
        pass
mock_win32serviceutil.ServiceFramework = MockServiceFramework

mock_win32service = MagicMock()
mock_win32service.SERVICE_STOP_PENDING = 3

mock_win32event = MagicMock()
mock_win32event.CreateEvent.return_value = "mock_event"

mock_servicemanager = MagicMock()
mock_servicemanager.EVENTLOG_INFORMATION_TYPE = 1
mock_servicemanager.PYS_SERVICE_STARTED = 2

sys.modules["win32serviceutil"] = mock_win32serviceutil
sys.modules["win32service"] = mock_win32service
sys.modules["win32event"] = mock_win32event
sys.modules["servicemanager"] = mock_servicemanager

def get_service_class():
    """Helper to get the service class with proper mocks."""
    import os
    os.environ["TEST_MODE"] = "1"
    from backend.windows_service import AlluciBackendService
    return AlluciBackendService

def test_os_check_raises():
    with patch("sys.platform", "linux"):
        if "backend.windows_service" in sys.modules:
            del sys.modules["backend.windows_service"]
            
        with pytest.raises(ImportError) as excinfo:
            import backend.windows_service
            
        assert "Windows-only" in str(excinfo.value)

def test_service_init():
    cls = get_service_class()
    svc = cls(["arg1"])
    assert svc.is_running is True
    assert svc.stop_event == "mock_event"

def test_service_stop():
    cls = get_service_class()
    svc = cls(["arg1"])
    svc.ReportServiceStatus = MagicMock()
    
    svc.SvcStop()
    
    svc.ReportServiceStatus.assert_called_with(mock_win32service.SERVICE_STOP_PENDING)
    mock_win32event.SetEvent.assert_called_with("mock_event")
    assert svc.is_running is False

def test_service_run():
    cls = get_service_class()
    svc = cls(["arg1"])
    svc.main = MagicMock()
    
    svc.SvcDoRun()
    
    mock_servicemanager.LogMsg.assert_called()
    svc.main.assert_called_once()

@pytest.mark.asyncio
async def test_service_main():
    cls = get_service_class()
    svc = cls(["arg1"])
    svc.is_running = False # to break check_stop loop immediately
    
    with patch("uvicorn.Server") as MockServer, \
         patch("asyncio.get_event_loop") as mock_loop:
        
        mock_server_instance = MockServer.return_value
        
        async def mock_serve(): pass
        async def mock_shutdown(): pass
        
        mock_server_instance.serve.return_value = mock_serve()
        mock_server_instance.shutdown.return_value = mock_shutdown()
        
        mock_loop_instance = MagicMock()
        mock_loop.return_value = mock_loop_instance
        
        # Capture the coroutine passed to run_until_complete and actually await it
        gathered_coro = None
        def fake_run(coro):
            nonlocal gathered_coro
            gathered_coro = coro
            
        mock_loop_instance.run_until_complete.side_effect = fake_run
        
        svc.main()
        
        assert mock_loop_instance.run_until_complete.called
        if gathered_coro:
            await gathered_coro

def test_windows_service_dunder_main():
    import sys
    import runpy
    import os
    
    os.environ["TEST_MODE"] = "1"
    mock_svcmanager = sys.modules["servicemanager"]
    mock_win32 = sys.modules["win32serviceutil"]
    
    mock_svcmanager.reset_mock()
    mock_win32.reset_mock()
    
    # Test len(sys.argv) == 1 branch
    with patch("sys.argv", ["script"]):
        runpy.run_module("backend.windows_service", run_name="__main__")
        
        mock_svcmanager.Initialize.assert_called_once()
        mock_svcmanager.StartServiceCtrlDispatcher.assert_called_once()
    
    # Test len(sys.argv) > 1 branch
    mock_svcmanager.reset_mock()
    with patch("sys.argv", ["script", "start"]):
        runpy.run_module("backend.windows_service", run_name="__main__")
        
        mock_win32.HandleCommandLine.assert_called_once()
