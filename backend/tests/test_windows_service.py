import pytest
import sys
import asyncio

# Skip all tests in this file if not on Windows
if sys.platform != "win32":
    pytest.skip("skipping windows-only tests", allow_module_level=True)

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
    # Mock msvcrt, ctypes.windll, and click._winconsole to prevent uvicorn/click import errors on macOS
    sys.modules["msvcrt"] = MagicMock()
    sys.modules["click._winconsole"] = MagicMock()
    import ctypes
    if not hasattr(ctypes, "windll"):
        ctypes.windll = MagicMock()
        
    with patch("sys.platform", "win32"):
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
    
    with patch("uvicorn.Server") as MockServer, \
         patch("asyncio.get_event_loop") as mock_loop:
        
        mock_server_instance = MockServer.return_value
        mock_server_instance.serve = AsyncMock()
        mock_server_instance.shutdown = AsyncMock()
        
        mock_loop_instance = MagicMock()
        mock_loop.return_value = mock_loop_instance
        
        def fake_run(coro):
            asyncio.run(coro)
            
        mock_loop_instance.run_until_complete.side_effect = fake_run
        
        async def stop_soon():
            await asyncio.sleep(0.1)
            svc.is_running = False
            
        asyncio.create_task(stop_soon())
        
        svc.main()
        
        assert mock_loop_instance.run_until_complete.called
