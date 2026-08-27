import asyncio
import os
from dotenv import load_dotenv

load_dotenv()
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

async def main():
    slack_bot_auth = os.environ.get("SLACK_BOT_TOKEN")
    slack_app_auth = os.environ.get("SLACK_APP_TOKEN")
    print(f"Bot auth key: {slack_bot_auth[:10] if slack_bot_auth else 'None'}...")
    print(f"App auth key: {slack_app_auth[:10] if slack_app_auth else 'None'}...")
    
    app_opts = {"token": slack_bot_auth}
    app = AsyncApp(**app_opts)
    try:
        auth_test = await app.client.auth_test()
        print(f"Auth test successful: {auth_test.get('user_id')}")
        
        # Test socket mode
        print("Starting socket mode connection test...")
        handler = AsyncSocketModeHandler(app, app_token)
        await handler.client.connect()
        print("Socket Mode connected successfully!")
        await handler.client.close()
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
