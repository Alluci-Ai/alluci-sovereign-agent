#!/usr/bin/env python3
import subprocess

def send_imessage(recipient: str, content: str):
    safe_content   = content.replace("\\", "\\\\").replace('"', '\\"')
    safe_recipient = recipient.replace("\\", "\\\\").replace('"', '\\"')

    script = f'''
    tell application "Messages"
        set targetService to 1st service whose service type = iMessage
        set targetBuddy to buddy "{safe_recipient}" of targetService
        send "{safe_content}" to targetBuddy
    end tell
    '''
    print(f"Attempting to send iMessage to {recipient}...")
    try:
        r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=15)
        if r.returncode == 0:
            print("✅ Message sent successfully via native AppleScript!")
        else:
            print(f"❌ Failed to send: {r.stderr.strip()}")
    except Exception as e:
        print(f"❌ Exception: {e}")

send_imessage("+16265090078", "Hello from the Alluci Sovereign Agent! 🌐 This is a native, locally executed test utilizing the Bridge Architecture.")
