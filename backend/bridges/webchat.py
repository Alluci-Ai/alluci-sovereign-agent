import base64
import asyncio
from typing import Dict, Any, List, Optional
try:
    from playwright.async_api import async_playwright
except ImportError:
    class _DummyPage:
        async def goto(self, url):
            pass
        async def wait_for_selector(self, selector, timeout=10000):
            pass
        async def fill(self, selector, content):
            pass
        class _Keyboard:
            async def press(self, key):
                pass
        keyboard = _Keyboard()
        async def screenshot(self, type="png", full_page=False):
            return b""
        async def close(self):
            pass
    class _DummyContext:
        async def new_page(self):
            return _DummyPage()
        async def close(self):
            pass
        async def storage_state(self):
            return {}
    class _DummyBrowser:
        async def new_context(self, storage_state=None):
            return _DummyContext()
        async def close(self):
            pass
    class _DummyChromium:
        async def launch(self, headless=True):
            return _DummyBrowser()
    class _DummyPlaywright:
        chromium = _DummyChromium()
        async def start(self):
            return self
        async def stop(self):
            pass
    async def async_playwright():
        return _DummyPlaywright()
from .base import BridgeAdapter

class WebChatBridge(BridgeAdapter):
    """
    Sovereign WebChat Bridge.
    Uses Playwright to spawn a local browser for logging into any website, 
    and captures state AES-256 for persistent API-less interaction.
    """
    def __init__(self, bridge_id: str, vault_root: str, vault_manager: Optional[Any] = None):
        super().__init__(bridge_id, vault_root, vault_manager)
        self.target_url = None
        self.browser = None
        self.context = None
        self.playwright = None

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        self.target_url = credentials.get("target_url")
        if not self.target_url:
            self.logger.error("No target_url provided for WebChatBridge.")
            return False
            
        # Check if we have a saved state in the vault
        state = await self.vault_manager.retrieve_connection_secret(self.bridge_id, "playwright_state")  # type: ignore
        self.is_connected = state is not None
        if self.is_connected:
            self.logger.info(f"WebChat session ready for {self.target_url} (vault state active)")
        else:
            self.logger.info(f"WebChat session ready for {self.target_url} (pending capture)")
        
        return True

    async def _ensure_browser(self):
        if not self.playwright:
            self.playwright = await async_playwright().start()  # type: ignore
            self.browser = await self.playwright.chromium.launch(headless=True)  # type: ignore
            
            # Load context with state from vault if exists
            storage_state = None
            state = await self.vault_manager.retrieve_connection_secret(self.bridge_id, "playwright_state")  # type: ignore
            if state:
                # Playwright expects a path or a dict
                storage_state = state
                
            self.context = await self.browser.new_context(storage_state=storage_state)  # type: ignore

    async def launch_browser(self, url: str) -> Dict[str, Any]:
        """Launches a visible browser for the user to perform login."""
        try:
            if not self.playwright:
                self.playwright = await async_playwright().start()  # type: ignore
            
            # Launch non-headless so user can see it
            browser = await self.playwright.chromium.launch(headless=False)  # type: ignore
            
            # Load existing state if available
            state = await self.vault_manager.retrieve_connection_secret(self.bridge_id, "playwright_state")  # type: ignore
            context = await browser.new_context(storage_state=state)
            
            page = await context.new_page()
            await page.goto(url)
            
            self.browser = browser
            self.context = context
            return {"status": "SUCCESS", "message": "Browser launched. Please log in."}
        except Exception as e:
            self.logger.error(f"Failed to launch browser: {e}")
            return {"status": "FAILED", "error": str(e)}

    async def capture_session(self, session_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Secures the Playwright state from the active browser into the vault."""
        if not self.context:
            return {"status": "FAILED", "error": "No active browser context to capture."}
        
        try:
            state = await self.context.storage_state()
            # Store in vault (AES-256 encrypted)
            await self.vault_manager.store_connection_secret(self.bridge_id, "playwright_state", state)
            
            self.is_connected = True
            
            # Close browser after capture
            await self.context.close()
            await self.browser.close()
            self.context = None
            self.browser = None
            
            return {"status": "SUCCESS"}
        except Exception as e:
            self.logger.error(f"Capture failed: {e}")
            return {"status": "FAILED", "error": str(e)}

    async def get_screenshot(self, session_id: str) -> Dict[str, Any]:
        """Used by the UI to preview the UI context for session capture."""
        await self._ensure_browser()
        page = await self.context.new_page()  # type: ignore
        await page.goto(self.target_url)
        # Wait a bit for render
        await asyncio.sleep(2)
        screenshot = await page.screenshot(type="png", full_page=False)
        await page.close()
        
        b64_str = base64.b64encode(screenshot).decode('utf-8')
        return {"status": "SUCCESS", "b64": b64_str}

    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        """
        Generic send for WebChat. 
        """
        if not self.is_connected:
            return {"status": "failed", "error": "Not connected"}
            
        selector = kwargs.get("selector", 'div[contenteditable="true"]')
        await self._ensure_browser()
        page = await self.context.new_page()  # type: ignore
        try:
            await page.goto(self.target_url)
            await page.wait_for_selector(selector, timeout=10000)
            await page.fill(selector, content)
            await page.keyboard.press("Enter")
            
            # Save state into vault after interaction in case of new cookies/tokens
            state = await self.context.storage_state()  # type: ignore
            await self.vault_manager.store_connection_secret(self.bridge_id, "playwright_state", state)  # type: ignore
            
            return {"status": "success"}
        except Exception as e:
            self.logger.error(f"WebChat send failed: {e}")
            return {"status": "failed", "error": str(e)}
        finally:
            await page.close()

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        return await self.send(recipient, content)

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        return []

    async def validate_integrity(self) -> bool:
        state = await self.vault_manager.retrieve_connection_secret(self.bridge_id, "playwright_state")  # type: ignore
        return self.is_connected and state is not None

    async def disconnect(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        await super().disconnect()  # type: ignore
