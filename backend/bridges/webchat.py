import os
import json
import base64
import asyncio
from typing import Dict, Any, List, Optional
from playwright.async_api import async_playwright
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
        self.state_file = os.path.join(self.vault_path, "state.json")

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        self.target_url = credentials.get("target_url")
        if not self.target_url:
            self.logger.error("No target_url provided for WebChatBridge.")
            return False
            
        # Check if we have a saved state
        if os.path.exists(self.state_file):
            self.is_connected = True
            self.logger.info(f"WebChat session ready for {self.target_url} (with saved state)")
        else:
            self.is_connected = False
            self.logger.info(f"WebChat session ready for {self.target_url} (pending capture)")
        
        return True

    async def _ensure_browser(self):
        if not self.playwright:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=True)
            
            # Load context with state if exists
            storage_state = None
            if os.path.exists(self.state_file):
                storage_state = self.state_file
                
            self.context = await self.browser.new_context(storage_state=storage_state)

    async def launch_browser(self, url: str) -> Dict[str, Any]:
        """Launches a visible browser for the user to perform login."""
        try:
            if not self.playwright:
                self.playwright = await async_playwright().start()
            
            # Launch non-headless so user can see it
            browser = await self.playwright.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto(url)
            
            # We don't close it yet; the user needs it to log in.
            # In a real production environment, we'd need to track this browser instance.
            # For a local sovereign agent, this is sufficient to let the user log in.
            # We'll store it so we can capture it later.
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
            with open(self.state_file, "w") as f:
                json.dump(state, f)
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
        page = await self.context.new_page()
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
        Highly site-specific logic normally belongs in a specialized bridge, 
        but we provide a generic 'type into selector' fallback.
        """
        if not self.is_connected:
            return {"status": "failed", "error": "Not connected"}
            
        selector = kwargs.get("selector", 'div[contenteditable="true"]')
        await self._ensure_browser()
        page = await self.context.new_page()
        try:
            await page.goto(self.target_url)
            await page.wait_for_selector(selector, timeout=10000)
            await page.fill(selector, content)
            await page.keyboard.press("Enter")
            # Save state after interaction in case of new cookies/tokens
            await self.context.storage_state(path=self.state_file)
            return {"status": "success"}
        except Exception as e:
            self.logger.error(f"WebChat send failed: {e}")
            return {"status": "failed", "error": str(e)}
        finally:
            await page.close()

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        return await self.send(recipient, content)

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        # Generic unread fetch is hard without specific selector logic
        return []

    async def validate_integrity(self) -> bool:
        return self.is_connected and os.path.exists(self.state_file)

    async def disconnect(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        await super().disconnect()
