
import asyncio
import os
import json
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Dict, Any, Optional
from .base import BridgeAdapter
from .gmail import MLStripper
import re

class EmailBridge(BridgeAdapter):
    """
    Production Email Bridge implementing SMTP/IMAP standards.
    Adheres to Simplicial Vault Isolation by persisting all traffic to the local vault.
    """
    def __init__(self, bridge_id: str, vault_root: str, vault_manager: Optional[Any] = None):
        super().__init__(bridge_id, vault_root, vault_manager)
        self.smtp_server = None
        self.smtp_port = 587
        self.imap_server = None
        self.imap_port = 993
        self.username = None
        self.password = None

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """
        Connects to SMTP and IMAP servers using provided credentials.
        """
        self.username = credentials.get("email")
        self.password = credentials.get("password")
        self.smtp_server = credentials.get("smtp_server", "smtp.gmail.com")
        self.smtp_port = int(credentials.get("smtp_port", 587))
        self.imap_server = credentials.get("imap_server", "imap.gmail.com")
        self.imap_port = int(credentials.get("imap_port", 993))

        if not self.username or not self.password:
             self.logger.error("Missing email credentials.")
             return False

        try:
            # Validate connections in non-blocking threads
            await asyncio.to_thread(self._test_smtp_connection)
            await asyncio.to_thread(self._test_imap_connection)
            
            self.is_connected = True
            self.logger.info(f"Email Bridge Connected: {self.username}")
            
            # Start polling loop automatically upon connection
            self._poll_task = asyncio.create_task(self._poll_loop())
            
            return True
        except Exception as e:
            self.logger.error(f"Email Connection Failed: {e}")
            self.is_connected = False
            return False

    def _test_smtp_connection(self):
        server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10)  # type: ignore
        server.starttls()
        server.login(self.username, self.password)  # type: ignore
        server.quit()

    def _test_imap_connection(self):
        mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)  # type: ignore
        mail.login(self.username, self.password)  # type: ignore
        mail.logout()

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        """
        Sends an email via SMTP and persists the record to the vault.
        """
        if not self.is_connected:
            return {"status": "failed", "error": "Bridge Disconnected"}
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.username  # type: ignore
            msg['To'] = recipient
            msg['Subject'] = "Message from Alluci Sovereign Agent"
            msg.attach(MIMEText(content, 'plain'))

            await asyncio.to_thread(self._send_smtp, msg)
            
            timestamp = datetime.now().isoformat()
            self._persist_to_vault("sent", {
                "recipient": recipient,
                "content": content,
                "timestamp": timestamp,
                "protocol": "SMTP"
            })
            
            return {"status": "success", "recipient": recipient, "timestamp": timestamp}
        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")
            return {"status": "failed", "error": f"Bridge communication error: {type(e).__name__}"}

    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        """Canonical data transmission method (Email)."""
        return await self.send_message(recipient, content)

    def _send_smtp(self, msg):
        server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30)  # type: ignore
        server.starttls()
        server.login(self.username, self.password)  # type: ignore
        server.send_message(msg)
        server.quit()

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Fetches unread emails via IMAP and persists them to the vault.
        """
        if not self.is_connected:
            return []
        
        try:
            return await asyncio.to_thread(self._fetch_imap, limit)
        except Exception as e:
            self.logger.error(f"Failed to fetch emails: {e}")
            return []

    def _fetch_imap(self, limit: int) -> List[Dict[str, Any]]:
        mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)  # type: ignore
        mail.login(self.username, self.password)  # type: ignore
        mail.select('inbox')
        
        status, messages = mail.search(None, '(UNSEEN)')
        if status != "OK" or not messages or not messages[0]:
            mail.close()
            mail.logout()
            return []

        email_ids = messages[0].split()
        results = []
        
        # Fetch latest 'limit' messages
        for e_id in email_ids[-limit:]:
            _, msg_data = mail.fetch(e_id, '(BODY[])')
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject = msg["subject"]
                    sender = msg["from"]
                    body = ""
                    
                    if msg.is_multipart():
                        html_body = ""
                        for part in msg.walk():
                            ctype = part.get_content_type()
                            if ctype == "text/plain":
                                body = part.get_payload(decode=True).decode(errors='ignore')  # type: ignore
                                break
                            elif ctype == "text/html":
                                html_body = part.get_payload(decode=True).decode(errors='ignore')  # type: ignore
                        if not body and html_body:
                            try:
                                s = MLStripper()
                                s.feed(html_body)
                                body = re.sub(r'\n\s*\n', '\n\n', s.get_data()).strip()
                            except Exception:
                                body = html_body
                    else:
                        body_content = msg.get_payload(decode=True).decode(errors='ignore')  # type: ignore
                        if msg.get_content_type() == "text/html":
                            try:
                                s = MLStripper()
                                s.feed(body_content)
                                body = re.sub(r'\n\s*\n', '\n\n', s.get_data()).strip()
                            except Exception:
                                body = body_content
                        else:
                            body = body_content
                    
                    data = {
                        "id": e_id.decode(),
                        "from": sender,
                        "subject": subject,
                        "body": body,
                        "timestamp": datetime.now().isoformat(),
                        "protocol": "EMAIL"
                    }
                    results.append(data)
                    
                    # Persist to vault
                    self._persist_to_vault("inbox", data)
                    
        mail.close()
        mail.logout()
        return results

    async def _poll_loop(self):
        """Autonomous polling loop for new emails."""
        self.logger.info("[ EMAIL ] Background polling loop started.")
        while self.is_connected:
            try:
                unread = await self.fetch_unread(limit=5)
                self.logger.info(f"[ EMAIL ] poll loop fetched {len(unread)} unread emails.")
                for msg in unread:
                    await self._dispatch_inbound(msg)
                
                # Poll every 60 seconds
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"[ EMAIL ] Poll loop error: {e}")
                await asyncio.sleep(60)

    def _persist_to_vault(self, box: str, data: Dict[str, Any]):
        """
        Writes structured data to the isolated bridge vault.
        """
        path = os.path.join(self.vault_path, f"{box}.jsonl")
        try:
            with open(path, "a") as f:
                f.write(json.dumps(data) + "\n")
        except Exception as e:
            self.logger.error(f"Vault Write Error: {e}")

    async def validate_integrity(self) -> bool:
        """
        Verifies connectivity to IMAP server.
        """
        try:
             await asyncio.to_thread(self._test_imap_connection)
             return True
        except Exception:
             self.is_connected = False
             return False
