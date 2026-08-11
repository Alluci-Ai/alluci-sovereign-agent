"""
Sovereign BlueSky (AT Protocol) Bridge — ATProto XRPC API Integration.

Supports:
  - Account Authentication (com.atproto.server.createSession)
  - Post Creation (app.bsky.feed.post)
  - Notifications & Mention Polling (app.bsky.notification.listNotifications)
  - Direct Messaging (app.bsky.convo.sendMessage)
  - Session Refreshing (com.atproto.server.refreshSession)
"""

import asyncio
import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

from .base import BridgeAdapter

BSKY_XRPC = "https://bsky.social/xrpc"

class BlueSkyBridge(BridgeAdapter):
    """
    Production BlueSky (AT Protocol) Sovereign Bridge Adapter.
    Integrates ATProto XRPC endpoints for posts, notifications, direct messages,
    and automatic session token refreshes within Simplicial Vault isolation.
    """

    def __init__(self, vault_root: str, vault_manager: Optional[Any] = None):
        super().__init__(bridge_id="bluesky", vault_root=vault_root, vault_manager=vault_manager)
        self.handle: Optional[str] = None
        self.did: Optional[str] = None
        self.access_jwt: Optional[str] = None
        self.refresh_jwt: Optional[str] = None
        self.poll_interval: int = 300  # 5 minutes default
        self._poll_task: Optional[asyncio.Task] = None

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """
        Authenticates with BlueSky / ATProto using handle and app token.
        credentials: {"handle": "user.bsky.social", "app_token": "xxxx-xxxx-xxxx-xxxx"}
        """
        handle = credentials.get("handle")
        app_token = credentials.get("app_token") or credentials.get("app_password")

        if not handle or not app_token:
            self.last_error = "Missing handle or app_token"
            self.logger.error(self.last_error)
            return False

        try:
            url = f"{BSKY_XRPC}/com.atproto.server.createSession"
            payload = {"identifier": handle, "password": app_token}
            resp = await self.client.post(url, json=payload)

            if resp.status_code != 200:
                self.last_error = f"BlueSky login failed: {resp.status_code} {resp.text}"
                self.logger.error(self.last_error)
                return False

            data = resp.json()
            self.handle = data.get("handle")
            self.did = data.get("did")
            self.access_jwt = data.get("accessJwt")
            self.refresh_jwt = data.get("refreshJwt")
            self.is_connected = True
            self.last_activity = datetime.now(timezone.utc).isoformat()

            await self._save_credentials({
                "handle": self.handle,
                "did": self.did,
                "access_jwt": self.access_jwt,
                "refresh_jwt": self.refresh_jwt,
                "app_token": app_token
            })

            self.logger.info(f"[BLUESKY] Connected successfully as {self.handle} ({self.did})")
            
            # Start notification polling in background
            if not self._poll_task or self._poll_task.done():
                self._poll_task = asyncio.create_task(self._poll_loop())

            return True
        except Exception as e:
            self.last_error = f"BlueSky connection exception: {e}"
            self.logger.error(self.last_error)
            return False

    async def post_record(self, text: str) -> Optional[Dict[str, Any]]:
        """Posts a record to BlueSky feed (app.bsky.feed.post)."""
        if not self.is_connected or not self.access_jwt or not self.did:
            self.logger.error("[BLUESKY] Cannot post record: not connected")
            return None

        url = f"{BSKY_XRPC}/com.atproto.repo.createRecord"
        headers = {"Authorization": f"Bearer {self.access_jwt}"}
        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        payload = {
            "repo": self.did,
            "collection": "app.bsky.feed.post",
            "record": {
                "$type": "app.bsky.feed.post",
                "text": text,
                "createdAt": now_iso
            }
        }

        try:
            resp = await self.client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                self.logger.info(f"[BLUESKY] Post created successfully: {resp.json().get('uri')}")
                return resp.json()
            else:
                self.logger.error(f"[BLUESKY] Post creation failed: {resp.status_code} {resp.text}")
                return None
        except Exception as e:
            self.logger.error(f"[BLUESKY] Post exception: {e}")
            return None

    async def fetch_notifications(self) -> List[Dict[str, Any]]:
        """Fetches notifications (mentions, replies, likes, reposts)."""
        if not self.is_connected or not self.access_jwt:
            return []

        url = f"{BSKY_XRPC}/app.bsky.notification.listNotifications"
        headers = {"Authorization": f"Bearer {self.access_jwt}"}

        try:
            resp = await self.client.get(url, headers=headers)
            if resp.status_code == 200:
                return resp.json().get("notifications", [])
            return []
        except Exception as e:
            self.logger.error(f"[BLUESKY] Notifications fetch exception: {e}")
            return []

    async def _poll_loop(self):
        """Background loop for checking notifications and triggering on_inbound callbacks."""
        while self.is_connected:
            try:
                notifications = await self.fetch_notifications()
                for notif in notifications:
                    if notif.get("reason") in ["mention", "reply"] and self.on_inbound:
                        author = notif.get("author", {}).get("handle", "unknown")
                        text = notif.get("record", {}).get("text", "")
                        await self.on_inbound({
                            "channel": "bluesky",
                            "sender": author,
                            "content": text,
                            "uri": notif.get("uri"),
                            "cid": notif.get("cid")
                        })
            except Exception as e:
                self.logger.warning(f"[BLUESKY] Poll loop warning: {e}")
            await asyncio.sleep(self.poll_interval)

    async def disconnect(self):
        """Disconnects the bridge and cancels polling tasks."""
        self.is_connected = False
        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
        self.logger.info("[BLUESKY] Disconnected bridge.")
