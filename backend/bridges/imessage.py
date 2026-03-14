"""
Sovereign iMessage Bridge for macOS.

Inbound: Reads from ~/Library/Messages/chat.db via sqlite3.
Outbound: Injects messages via osascript (AppleScript).

Requires macOS with:
  - Full Disk Access granted to the running process
  - Automation permission for Messages.app
  - (Optional) Contacts permission for contact name resolution
"""

import asyncio
import json
import os
import platform
import subprocess
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .base import BridgeAdapter


class IMessageBridge(BridgeAdapter):
    """
    Production iMessage Bridge.
    - Non-blocking subprocess calls via run_in_executor
    - Vault-persisted rowid cursor (no duplicate dispatch on restart)
    - In-process GUID deduplication set
    - Enriched SQL (group chat names + attachment filenames)
    """

    CURSOR_KEY = "imessage_last_rowid"
    DEDUP_MAXSIZE = 2_000

    def __init__(self, bridge_id: str, vault_root: str, vault_manager: Optional[Any] = None):
        super().__init__(bridge_id, vault_root, vault_manager)
        self.is_macos: bool = platform.system() == "Darwin"
        self._poll_task: Optional[asyncio.Task] = None
        self._last_rowid: int = 0
        self._seen_guids: set = set()

        if not self.is_macos:
            self.logger.warning(
                f"[IMESSAGE] Disabled — platform is {platform.system()}, not macOS."
            )

    # ── Helpers ──────────────────────────────────────────────────────────────

    async def _run(self, func, *args):
        """Run a blocking function in the default thread pool executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args)

    def _load_cursor(self) -> int:
        """Load the persisted rowid cursor from the vault."""
        path = os.path.join(self.vault_path, "cursor.json")
        try:
            if os.path.exists(path):
                with open(path) as f:
                    return json.load(f).get("last_rowid", 0)
        except Exception:
            pass
        return 0

    def _save_cursor(self, rowid: int) -> None:
        """Persist the rowid cursor to the vault."""
        path = os.path.join(self.vault_path, "cursor.json")
        try:
            with open(path, "w") as f:
                json.dump({"last_rowid": rowid}, f)
            os.chmod(path, 0o600)
        except Exception as e:
            self.logger.warning(f"[IMESSAGE] Failed to persist cursor: {e}")

    # ── Permissions ──────────────────────────────────────────────────────────

    def _check_permissions_sync(self) -> Dict[str, bool]:
        """Synchronous permission probe — call via _run()."""
        db = os.path.expanduser("~/Library/Messages/chat.db")
        fda = os.access(db, os.R_OK)

        auto_msg = False
        try:
            r = subprocess.run(
                ["osascript", "-e", 'tell application "Messages" to return name'],
                capture_output=True, text=True, timeout=3,
            )
            auto_msg = r.returncode == 0
        except Exception:
            pass

        contacts = False
        try:
            r = subprocess.run(
                ["osascript", "-e", 'tell application "Contacts" to return name'],
                capture_output=True, text=True, timeout=3,
            )
            contacts = r.returncode == 0
        except Exception:
            pass

        return {
            "full_disk_access":  fda,
            "automation_messages": auto_msg,
            "contacts":          contacts,
            "all_granted":       fda and auto_msg,
        }

    async def check_permission(self) -> Dict[str, bool]:
        if not self.is_macos:
            return {"error": "macOS required"}
        return await self._run(self._check_permissions_sync)

    # ── Connection ───────────────────────────────────────────────────────────

    async def connect(self, credentials: Optional[Dict[str, Any]] = None) -> bool:
        if not self.is_macos:
            self.last_error = "iMessage requires macOS."
            return False

        perms = await self.check_permission()
        if not perms.get("all_granted"):
            self.last_error = "Missing Full Disk Access or Automation permission."
            self.logger.error(f"[IMESSAGE] {self.last_error}")
            return False

        # Restore cursor from vault (prevents duplicate dispatch on restart)
        self._last_rowid = self._load_cursor()
        self.logger.info(
            f"[IMESSAGE] Resuming from rowid cursor {self._last_rowid}."
        )

        self.is_connected = True
        self._poll_task = asyncio.create_task(self._poll_loop())
        self.logger.info("[IMESSAGE] Bridge anchored to Messages.app.")
        return True

    # ── Poll Loop ────────────────────────────────────────────────────────────

    async def _poll_loop(self) -> None:
        """Poll chat.db for new messages every 30 seconds."""
        self.logger.info("[IMESSAGE] Poll loop started.")
        while self.is_connected:
            try:
                new_msgs = await self.fetch_unread(limit=50)
                for msg in new_msgs:
                    guid = msg.get("id")
                    if guid and guid in self._seen_guids:
                        continue                            # In-process dedup
                    if guid:
                        self._seen_guids.add(guid)
                        # Trim dedup set to prevent unbounded growth
                        if len(self._seen_guids) > self.DEDUP_MAXSIZE:
                            # Pop an arbitrary element if pop() behaves like set.pop()
                            # or use a list/deque if ordering matters. 
                            # set.pop() removes an arbitrary element.
                            self._seen_guids.pop()

                    await self._dispatch_inbound(msg)

                if new_msgs:
                    # Persist the highest rowid we've processed
                    self._save_cursor(self._last_rowid)
                    self.last_activity = datetime.now(timezone.utc).isoformat()

            except asyncio.CancelledError:
                self.logger.info("[IMESSAGE] Poll loop cancelled.")
                return
            except Exception as e:
                self.logger.error(f"[IMESSAGE] Poll error: {e}", exc_info=True)

            await asyncio.sleep(30)

    # ── Fetch Unread ─────────────────────────────────────────────────────────

    def _query_chat_db_sync(self, cursor: int, limit: int) -> List[Dict[str, Any]]:
        """
        Blocking SQLite query — run via _run() to avoid blocking the event loop.
        Returns messages with rowid > cursor, including group chat names and attachments.
        """
        db_path = os.path.expanduser("~/Library/Messages/chat.db")
        if not os.path.exists(db_path):
            return []

        # Apple's epoch offset: macOS timestamps start at 2001-01-01 (Unix: 978307200)
        APPLE_EPOCH_OFFSET = 978_307_200

        query = f"""
        SELECT
            message.ROWID                                            AS rowid,
            message.guid                                             AS guid,
            handle.id                                                AS sender,
            COALESCE(chat.display_name, chat.chat_identifier, '')    AS chat_name,
            chat.chat_identifier                                     AS chat_id,
            message.text,
            message.date / 1000000000 + {APPLE_EPOCH_OFFSET}       AS ts,
            message.is_from_me,
            GROUP_CONCAT(attachment.filename, '|||')                 AS attachments
        FROM message
        LEFT JOIN handle             ON message.handle_id = handle.ROWID
        LEFT JOIN chat_message_join  ON chat_message_join.message_id = message.ROWID
        LEFT JOIN chat               ON chat.ROWID = chat_message_join.chat_id
        LEFT JOIN message_attachment_join
                                     ON message_attachment_join.message_id = message.ROWID
        LEFT JOIN attachment         ON attachment.ROWID = message_attachment_join.attachment_id
        WHERE message.is_from_me = 0
          AND message.ROWID > {cursor}
        GROUP BY message.ROWID
        ORDER BY message.ROWID ASC
        LIMIT {limit};
        """

        try:
            result = subprocess.run(
                ["sqlite3", db_path, "-json", query],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0 or not result.stdout.strip():
                return []

            rows = json.loads(result.stdout)
            messages = []
            for row in rows:
                atts = []
                if row.get("attachments"):
                    for fn in row["attachments"].split("|||"):
                        if fn.strip():
                            atts.append(fn.strip())

                messages.append({
                    "id":          row.get("guid"),
                    "rowid":       row.get("rowid"),
                    "from":        row.get("sender"),
                    "body":        row.get("text") or "",
                    "chat_name":   row.get("chat_name"),
                    "chat_id":     row.get("chat_id"),
                    "attachments": atts,
                    "protocol":    "IMESSAGE",
                    "timestamp":   datetime.fromtimestamp(
                        row.get("ts", 0), tz=timezone.utc
                    ).isoformat(),
                })

            return messages
        except Exception as e:
            self.logger.debug(f"[IMESSAGE] SQLite query failed: {e}")
            return []

    async def fetch_unread(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch messages with ROWID > last known cursor. Non-blocking."""
        if not self.is_macos:
            return []

        msgs = await self._run(self._query_chat_db_sync, self._last_rowid, limit)

        # Advance the cursor to the highest rowid seen
        if msgs:
            self._last_rowid = max(m["rowid"] for m in msgs)

        return msgs

    # ── Send ────────────────────────────────────────────────────────────────

    def _send_applescript_sync(self, recipient: str, content: str) -> Dict[str, Any]:
        """Blocking AppleScript send — run via _run()."""
        # Escape double quotes to prevent AppleScript injection
        safe_content   = content.replace("\\", "\\\\").replace('"', '\\"')
        safe_recipient = recipient.replace("\\", "\\\\").replace('"', '\\"')

        script = f'''
        tell application "Messages"
            set targetService to 1st service whose service type = iMessage
            set targetBuddy to buddy "{safe_recipient}" of targetService
            send "{safe_content}" to targetBuddy
        end tell
        '''
        try:
            r = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=15,
            )
            if r.returncode == 0:
                return {"status": "success"}
            return {"status": "failed", "error": r.stderr.strip()}
        except subprocess.TimeoutExpired:
            return {"status": "failed", "error": "osascript timed out after 15s"}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        """Send an iMessage. Non-blocking — delegates to thread pool."""
        if not self.is_connected:
            return {"status": "failed", "error": self.last_error or "Bridge disconnected"}
        result = await self._run(self._send_applescript_sync, recipient, content)
        if result["status"] == "success":
            self.last_activity = datetime.now(timezone.utc).isoformat()
        else:
            self.last_error = result.get("error")
        return result

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        return await self.send(recipient, content)

    # ── Teardown ─────────────────────────────────────────────────────────────

    async def disconnect(self) -> None:
        self.is_connected = False
        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        self._save_cursor(self._last_rowid)
        await super().disconnect()
        self.logger.info("[IMESSAGE] Disconnected. Cursor persisted.")

    # ── Supporting Methods ───────────────────────────────────────────────────

    async def validate_integrity(self) -> bool:
        if not self.is_macos:
            return False
        perms = await self.check_permission()
        return bool(perms.get("full_disk_access"))

    def get_health(self) -> Dict[str, Any]:
        h = super().get_health()
        h.update({
            "platform":        platform.system(),
            "macos_native":    self.is_macos,
            "cursor_rowid":    self._last_rowid,
            "dedup_set_size":  len(self._seen_guids),
            "poll_active":     bool(self._poll_task and not self._poll_task.done()),
            "last_error":      self.last_error,
        })
        return h
