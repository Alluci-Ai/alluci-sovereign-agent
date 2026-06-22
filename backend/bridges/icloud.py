"""
Sovereign iCloud Bridge using pyicloud.

Features:
  - All pyicloud calls wrapped in run_in_executor (non-blocking)
  - Session cookies persisted to ICLOUD_COOKIE_DIR (2FA only on first connect)
  - on_event null guard (connect() no longer crashes when on_event is None)
  - Drive listing and file download
  - Reminders, Notes, and Contacts read access

Prerequisites:
  pip install pyicloud
"""

import asyncio
import os
from typing import Any, Dict, List, Optional

from .base import BridgeAdapter

try:
    from pyicloud import PyiCloudService
    from pyicloud.exceptions import PyiCloudAPIResponseException
    PYICLOUD_AVAILABLE = True
except ImportError:
    PyiCloudService = None
    PyiCloudAPIResponseException = Exception
    PYICLOUD_AVAILABLE = False


class ICloudBridge(BridgeAdapter):
    """
    Production iCloud Bridge.
    Wraps pyicloud in asyncio.run_in_executor for non-blocking operation.
    Persists session cookies so 2FA is only required on first connection.
    """

    def __init__(self, bridge_id: str, vault_root: str, vault_manager: Optional[Any] = None):
        super().__init__(bridge_id, vault_root, vault_manager)
        self.api: Optional["PyiCloudService"] = None
        self._apple_id: Optional[str] = None
        self._cookie_dir: Optional[str] = None

    # ── Async Helper ─────────────────────────────────────────────────────────

    async def _run(self, func, *args, **kwargs):
        """Run a blocking pyicloud call in the thread pool executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    # ── Connection ───────────────────────────────────────────────────────────

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """
        Connect to iCloud. Persists session cookies so 2FA is not required on restart.
        credentials:
            apple_id (str):              Apple ID email
            app_specific_password (str): App-specific password (required for 2FA accounts)
            password (str):              Plain password (fallback)
        """
        if not PYICLOUD_AVAILABLE:
            self.last_error = "pyicloud not installed. Run: pip install pyicloud"
            self.logger.error(f"[ICLOUD] {self.last_error}")
            return False

        from ..config import settings

        apple_id = credentials.get("apple_id")
        password = (
            credentials.get("app_specific_password")
            or credentials.get("password")
        )

        if not apple_id or not password:
            self.last_error = "apple_id and password (or app_specific_password) required."
            return False

        self._apple_id = apple_id
        self._cookie_dir = os.path.expanduser(settings.ICLOUD_COOKIE_DIR)  # type: ignore
        os.makedirs(self._cookie_dir, mode=0o700, exist_ok=True)  # type: ignore

        try:
            # PyiCloudService constructor is blocking — run in executor
            def _create_session():
                return PyiCloudService(
                    apple_id,
                    password,
                    cookie_directory=self._cookie_dir,
                )

            self.api = await self._run(_create_session)

            if await self._run(lambda: self.api.requires_2fa):
                self.logger.info(f"[ICLOUD] 2FA required for {apple_id}.")
                # Notify UI via on_event — null-guarded
                if self.on_event:
                    asyncio.create_task(self.on_event("bridge.status", {
                        "bridge_id": self.bridge_id,
                        "status":    "2FA_REQUIRED",
                        "apple_id":  apple_id,
                    }))
                return False  # Will complete via submit_2fa()

            self.is_connected = True
            self.session = {"apple_id": apple_id}
            self.logger.info(f"[ICLOUD] Session established for {apple_id} (cookies cached).")
            return True

        except Exception as e:
            self.last_error = str(e)
            self.logger.error(f"[ICLOUD] Connect failed: {e}")
            return False

    # ── 2FA ─────────────────────────────────────────────────────────────────

    async def submit_2fa(self, code: str) -> Dict[str, Any]:
        """Submit the 6-digit 2FA verification code."""
        if not self.api:
            return {"status": "FAILED", "error": "No active session."}

        try:
            result = await self._run(self.api.validate_2fa_code, code)
            if result:
                self.is_connected = True
                self.session = self.session or {"apple_id": self._apple_id}
                self.logger.info("[ICLOUD] 2FA verified. Session is now active.")

                # Notify UI — null-guarded
                if self.on_event:
                    asyncio.create_task(self.on_event("bridge.status", {
                        "bridge_id": self.bridge_id,
                        "status":    "CONNECTED",
                        "apple_id":  self._apple_id,
                    }))
                return {"status": "SUCCESS"}
            return {"status": "FAILED", "error": "Invalid 2FA code."}
        except Exception as e:
            self.logger.error(f"[ICLOUD] 2FA error: {e}")
            return {"status": "FAILED", "error": str(e)}

    # ── Drive ────────────────────────────────────────────────────────────────

    async def list_drive(self, path: str = "/") -> List[Dict[str, Any]]:
        """
        List files and directories in iCloud Drive.
        path: POSIX path relative to Drive root, e.g. "/Documents"
        """
        if not self.is_connected or not self.api:
            return []

        def _list():
            node = self.api.drive  # type: ignore
            for part in path.strip("/").split("/"):
                if part:
                    node = node[part]
            return [
                {
                    "name":      item.name,
                    "type":      item.type,          # "file" or "folder"
                    "size":      getattr(item, "size", None),
                    "date_changed": str(getattr(item, "date_changed", "")),
                    "date_modified": str(getattr(item, "date_modified", "")),
                }
                for item in node.dir()
            ]

        try:
            return await self._run(_list)
        except Exception as e:
            self.logger.error(f"[ICLOUD] Drive list failed: {e}")
            return []

    async def download_file(self, path: str, local_dest: str) -> Dict[str, Any]:
        """
        Download a file from iCloud Drive to a local path.
        path: POSIX path, e.g. "/Documents/report.pdf"
        local_dest: absolute local file path to write to
        """
        if not self.is_connected or not self.api:
            return {"status": "failed", "error": "Not connected"}

        def _download():
            node = self.api.drive  # type: ignore
            parts = path.strip("/").split("/")
            for part in parts[:-1]:
                node = node[part]
            item = node[parts[-1]]
            download = self.api.drive.get_file(item.drivewsid)  # type: ignore
            with open(local_dest, "wb") as f:
                f.write(download.raw.read())
            return os.path.getsize(local_dest)

        try:
            size = await self._run(_download)
            return {"status": "success", "local_path": local_dest, "size": size}
        except Exception as e:
            self.logger.error(f"[ICLOUD] Download failed: {e}")
            return {"status": "failed", "error": str(e)}

    # ── Reminders ────────────────────────────────────────────────────────────

    async def fetch_reminders(self) -> List[Dict[str, Any]]:
        """Fetch all incomplete reminders from iCloud Reminders."""
        if not self.is_connected or not self.api:
            return []

        def _fetch():
            reminders = []
            for collection in self.api.reminders.lists:  # type: ignore
                for item in collection.get("items", []):
                    if not item.get("completionDate"):
                        reminders.append({
                            "id":       item.get("guid"),
                            "title":    item.get("title"),
                            "due_date": item.get("dueDate"),
                            "priority": item.get("priority", 0),
                            "list":     collection.get("title"),
                        })
            return reminders

        try:
            return await self._run(_fetch)
        except Exception as e:
            self.logger.error(f"[ICLOUD] Reminders fetch failed: {e}")
            return []

    # ── Notes ────────────────────────────────────────────────────────────────

    async def fetch_notes(self) -> List[Dict[str, Any]]:
        """Fetch all notes from iCloud Notes."""
        if not self.is_connected or not self.api:
            return []

        def _fetch():
            result = []
            for folder in getattr(self.api, "notes", {}).values():
                for note in folder.get("notes", []):
                    result.append({
                        "id":       note.get("guid"),
                        "title":    note.get("title"),
                        "snippet":  note.get("snippet", ""),
                        "modified": str(note.get("modificationDate", "")),
                    })
            return result

        try:
            return await self._run(_fetch)
        except Exception as e:
            self.logger.error(f"[ICLOUD] Notes fetch failed: {e}")
            return []

    # ── Contacts ─────────────────────────────────────────────────────────────

    async def fetch_contacts(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch contacts from iCloud Contacts."""
        if not self.is_connected or not self.api:
            return []

        def _fetch():
            contacts = []
            for contact in list(self.api.contacts.all())[:limit]:  # type: ignore
                phones = [
                    p.get("field") for p in contact.get("phones", [])
                    if p.get("field")
                ]
                emails = [
                    e.get("field") for e in contact.get("emailAddresses", [])
                    if e.get("field")
                ]
                contacts.append({
                    "id":        contact.get("contactId"),
                    "first":     contact.get("firstName", ""),
                    "last":      contact.get("lastName", ""),
                    "phones":    phones,
                    "emails":    emails,
                    "company":   contact.get("companyName", ""),
                })
            return contacts

        try:
            return await self._run(_fetch)
        except Exception as e:
            self.logger.error(f"[ICLOUD] Contacts fetch failed: {e}")
            return []

    # ── Supporting Methods ───────────────────────────────────────────────────

    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        return {"status": "failed", "error": "Use the iMessage bridge for messaging."}

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        return await self.send(recipient, content)

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        """For iCloud, 'unread' means recent Drive changes — returns drive root listing."""
        return await self.list_drive("/")

    async def validate_integrity(self) -> bool:
        if not self.api or not self.is_connected:
            return False
        try:
            return await self._run(lambda: not self.api.requires_2fa)
        except Exception:
            return False

    def get_health(self) -> Dict[str, Any]:
        h = super().get_health()
        h.update({
            "apple_id":       self._apple_id,
            "cookie_dir":     self._cookie_dir,
            "pyicloud":       PYICLOUD_AVAILABLE,
            "requires_2fa":   (
                self.api.requires_2fa
                if self.api else None
            ),
        })
        return h
