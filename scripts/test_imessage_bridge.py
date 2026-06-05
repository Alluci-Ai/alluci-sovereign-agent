#!/usr/bin/env python3
import asyncio
import os
import sys

# Ensure backend module can be found
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.bridges.imessage import IMessageBridge

class MockVaultManager:
    vault_root = "/tmp/mock_vault"
    def __init__(self):
        os.makedirs(self.vault_root, exist_ok=True)
    async def retrieve_connection_secret(self, bridge_id, account_id):
        return {}
    async def store_connection_secret(self, bridge_id, account_id, data):
        pass

async def test_imessage():
    print("Initializing iMessage Bridge...")
    vault_manager = MockVaultManager()
    bridge = IMessageBridge(bridge_id="imessage_test", vault_root=vault_manager.vault_root, vault_manager=vault_manager)
    
    print("Connecting to local Messages.app...")
    connected = await bridge.connect()
    
    if not connected:
        print(f"Failed to connect. Error: {bridge.last_error}")
        print("Please ensure your Terminal/IDE has 'Full Disk Access' in System Settings.")
        return

    recipient = "+16265090078"
    message = "Hello from the Alluci Sovereign Agent! 🌐 This is a native, locally executed test utilizing the Bridge Architecture."
    
    print(f"Sending test message to {recipient}...")
    result = await bridge.send_message(recipient, message)
    
    if result.get("status") == "success":
        print("✅ Message successfully dispatched via AppleScript!")
    else:
        print(f"❌ Failed to send message: {result.get('error')}")

    # Disconnect to cleanup polling tasks
    await bridge.disconnect()

if __name__ == "__main__":
    asyncio.run(test_imessage())
