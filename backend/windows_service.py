import sys

if sys.platform != "win32":
    raise ImportError(
        "windows_service.py is Windows-only. "
        "Use `uvicorn backend.app:app` on Linux/macOS."
    )

import os
import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import logging
import asyncio
import uvicorn
from multiprocessing import Process

# Ensure we can import the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class AlluciBackendService(win32serviceutil.ServiceFramework):
    _svc_name_ = "AlluciSovereignAgent"
    _svc_display_name_ = "Alluci Sovereign Agent Backend"
    _svc_description_ = "Sovereign AI Executive Assistant Backend Service"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.socket_timeout = 10000 
        self.is_running = True

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        self.is_running = False

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        self.main()

    def main(self):
        # Start the FastAPI app in a separate process or thread
        # Using uvicorn.run directly here is possible but harder to stop gracefully
        from backend.app import app
        from backend.config import settings
        
        config = uvicorn.Config(
            app=app, 
            host=settings.HOST, 
            port=settings.PORT, 
            log_level="info"
        )
        server = uvicorn.Server(config)
        
        # Run server in a way that checks for the stop event
        loop = asyncio.get_event_loop()
        
        async def serve():
            await server.serve()
            
        async def check_stop():
            while self.is_running:
                await asyncio.sleep(1)
            await server.shutdown()
            
        loop.run_until_complete(asyncio.gather(serve(), check_stop()))

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(AlluciBackendService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(AlluciBackendService)
