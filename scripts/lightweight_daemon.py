#!/usr/bin/env python3
import time
import subprocess
import json
import os

LAST_ROWID = 0

def fetch_unread():
    global LAST_ROWID
    db_path = os.path.expanduser("~/Library/Messages/chat.db")
    # Apple's epoch offset: macOS timestamps start at 2001-01-01
    query = f"""
    SELECT message.ROWID as rowid, message.text as text, handle.id as sender 
    FROM message 
    LEFT JOIN handle ON message.handle_id = handle.ROWID 
    WHERE message.text NOT LIKE '🤖%' AND message.ROWID > {LAST_ROWID} 
    ORDER BY message.ROWID ASC LIMIT 5;
    """
    try:
        r = subprocess.run(["sqlite3", db_path, "-json", query], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            rows = json.loads(r.stdout)
            if rows:
                LAST_ROWID = max(r.get("rowid", LAST_ROWID) for r in rows)
                return rows
    except Exception as e:
        print(f"SQLite Error: {e}")
    return []

def send_reply(recipient, content):
    safe_content   = content.replace("\\", "\\\\").replace('"', '\\"')
    safe_recipient = recipient.replace("\\", "\\\\").replace('"', '\\"')
    script = f'''
    tell application "Messages"
        set targetService to 1st service whose service type = iMessage
        set targetBuddy to buddy "{safe_recipient}" of targetService
        send "{safe_content}" to targetBuddy
    end tell
    '''
    subprocess.run(["osascript", "-e", script])

print("========================================")
print("🧠 Sovereign Brain Daemon Boot Sequence Initiated...")
print("🛡️  Bridge Connected: iMessage")
print("========================================")

# Get latest rowid to ignore history
try:
    r = subprocess.run(["sqlite3", os.path.expanduser("~/Library/Messages/chat.db"), "SELECT MAX(ROWID) FROM message;"], capture_output=True, text=True)
    LAST_ROWID = int(r.stdout.strip() or 0)
    print(f"Anchored to chat history. Cursor: {LAST_ROWID}")
except Exception:
    pass

print("Listening for incoming texts...\n")

while True:
    new_msgs = fetch_unread()
    for msg in new_msgs:
        sender = msg.get("sender")
        text = msg.get("text")
        if text and sender:
            print(f"📥 Received from {sender}: {text}")
            reply = f"🤖 Sovereign Brain: I have received your prompt '{text}'. Processing via Gemma MLX..."
            send_reply(sender, reply)
            print(f"📤 Auto-replied to {sender}")
    time.sleep(3)
