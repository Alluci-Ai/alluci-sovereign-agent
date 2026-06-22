from ..logging_config import get_logger
import platform

logger = get_logger("WindowsNotifier")

class WindowsNotifier:
    """
    Handles native Windows 11 toast notifications.
    Requires: pip install win10toast-click
    """
    
    def __init__(self):
        self.enabled = platform.system() == "Windows"
        self.toaster = None
        if self.enabled:
            try:
                from win10toast_click import ToastNotifier
                self.toaster = ToastNotifier()
            except ImportError:
                logger.warning("win10toast-click not found. Windows notifications disabled.")
                self.enabled = False

    def notify(self, title: str, message: str, duration: int = 5, callback=None):
        """Sends a toast notification."""
        if not self.enabled or not self.toaster:
            logger.debug(f"Notification suppressed: {title}")
            return

        try:
            self.toaster.show_toast(
                title=title,
                msg=message,
                icon_path=None, # TBD: Add Alluci icon
                duration=duration,
                threaded=True,
                callback_on_click=callback
            )
        except Exception as e:
            logger.error(f"Failed to send Windows toast: {e}")

# Global instance
windows_notifier = WindowsNotifier()
