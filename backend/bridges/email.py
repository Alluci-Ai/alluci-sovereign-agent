
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

class EmailBridge(BridgeAdapter):
    """
    Production Email Bridge implementing SMTP/IMAP standards.
    Adheres to Simplicial Vault Isolation by persisting all traffic to the local vault.
    """
    def __init__(self, bridge_id: str, vault_root: str):
        super().__init__(bridge_id, vault_root)
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
            return True
        except Exception as e:
            self.logger.error(f"Email Connection Failed: {e}")
            self.is_connected = False
            return False

    def _test_smtp_connection(self):
        server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10)
        server.starttls()
        server.login(self.username, self.password)
        server.quit()

    def _test_imap_connection(self):
        mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
        mail.login(self.username, self.password)
        mail.logout()

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        """
        Sends an email via SMTP and persists the record to the vault.
        """
        if not self.is_connected:
            return {"status": "failed", "error": "Bridge Disconnected"}
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.username
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
            return {"status": "failed", "error": str(e)}

    def _send_smtp(self, msg):
        server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30)
        server.starttls()
        server.login(self.username, self.password)
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
        mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
        mail.login(self.username, self.password)
        mail.select('inbox')
        
        status, messages = mail.search(None, '(UNSEEN)')
        if status != "OK":
            mail.close()
            mail.logout()
            return []

        email_ids = messages[0].split()
        results = []
        
        # Fetch latest 'limit' messages
        for e_id in email_ids[-limit:]:
            _, msg_data = mail.fetch(e_id, '(RFC822)')
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject = msg["subject"]
                    sender = msg["from"]
                    body = ""
                    
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode(errors='ignore')
                                break
                    else:
                        body = msg.get_payload(decode=True).decode(errors='ignore')
                    
                    data = {
                        "id": e_id.decode(),
                        "from": sender,
                        "subject": subject,
                        "body": body,
                        "timestamp": datetime.now().isoformat(),
                        "protocol": "IMAP"
                    }
                    results.append(data)
                    
                    # Persist to vault
                    self._persist_to_vault("inbox", data)
                    
        mail.close()
        mail.logout()
        return results

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
        except:
             self.is_connected = False
             return False
