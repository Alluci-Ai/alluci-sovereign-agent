import pytest
pytestmark = pytest.mark.unit

from unittest.mock import MagicMock, AsyncMock, patch
import json
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.routers import channels
from backend import services
from sqlmodel import Session, create_engine, SQLModel
from backend.models import AgentChannelSubscription

# Setup temp database for subscriptions
@pytest.fixture
def temp_db_session():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

class MockAdapter:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

@pytest.fixture
def mock_adapters():
    # Setup mock channel adapters using MockAdapter to avoid mock attr auto-creation
    mock_discord = MockAdapter(
        channel_type="discord",
        status="connected",
        is_connected=True,
        last_activity=None,
        last_error=None,
        config={"token": "mock_token"},
        get_availability_status=lambda: {"id": "discord", "available": True},
        update_config=AsyncMock(return_value={"status": "updated"}),
        connect=AsyncMock(),
        disconnect=AsyncMock(),
        send=AsyncMock(return_value={"msg_id": "123"}),
        upload=AsyncMock(return_value={"file_id": "456"}),
        fetch_unread=AsyncMock(return_value=[{"id": "msg1", "text": "hello"}]),
        execute_social_task=AsyncMock(return_value={"task_id": "t1"}),
        execute_enterprise_task=AsyncMock(return_value={"task_id": "e1"}),
        validate_integrity=AsyncMock(return_value=True)
    )
    
    mock_wechat = MockAdapter(
        channel_type="wechat",
        status="idle",
        is_connected=False,
        last_activity=None,
        last_error=None,
        init_qr=AsyncMock(return_value={"url": "http://wechat.qr"}),
        verify_callback=lambda *args, **kwargs: "echostr",
        process_webhook=AsyncMock()
    )

    mock_telegram = MockAdapter(
        channel_type="telegram",
        status="idle",
        is_connected=True,
        bot_token="valid_token",
        last_activity=None,
        last_error=None,
        process_webhook=AsyncMock(return_value={"processed": True})
    )

    mock_slack = MockAdapter(
        channel_type="slack",
        status="idle",
        is_connected=False,
        last_activity=None,
        last_error=None,
        build_oauth_url=lambda *args, **kwargs: ("http://slack.auth", "verifier123"),
        verify_signature=lambda *args, **kwargs: True,
        process_webhook=AsyncMock(return_value={"ok": True})
    )

    registry = {
        "discord": mock_discord,
        "wechat": mock_wechat,
        "telegram": mock_telegram,
        "slack": mock_slack
    }
    
    with patch.dict(services.channel_registry, registry, clear=True):
        yield registry

class TestChannelsRouter:
    @pytest.mark.asyncio
    async def test_list_channels(self, app_client, auth_headers, mock_adapters):
        res = app_client.get("/api/v1/channels", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 4
        assert any(c["id"] == "discord" for c in data)

    @pytest.mark.asyncio
    async def test_get_channel_availability(self, app_client, auth_headers, mock_adapters):
        res = app_client.get("/api/v1/channels/availability", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        assert "discord" in [d.get("id") for d in data if d]

    @pytest.mark.asyncio
    async def test_get_channel_config(self, app_client, auth_headers, mock_adapters):
        res = app_client.get("/api/v1/channels/discord/config", headers=auth_headers)
        assert res.status_code == 200
        assert res.json() == {"token": "mock_token"}

    @pytest.mark.asyncio
    async def test_update_channel_config(self, app_client, auth_headers, mock_adapters):
        res = app_client.put("/api/v1/channels/discord/config", json={"token": "new_token"}, headers=auth_headers)
        assert res.status_code == 200
        assert res.json() == {"status": "updated"}

    @pytest.mark.asyncio
    async def test_toggle_channel(self, app_client, auth_headers, mock_adapters):
        res = app_client.put("/api/v1/channels/discord/toggle", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["status"] == "SUCCESS"
        mock_adapters["discord"].disconnect.assert_called_once()
        
        mock_adapters["discord"].is_connected = False
        res = app_client.put("/api/v1/channels/discord/toggle", headers=auth_headers)
        assert res.status_code == 200
        mock_adapters["discord"].connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_channel_send(self, app_client, auth_headers, mock_adapters):
        res = app_client.post("/api/v1/channels/discord/send", json={"recipient": "user1", "content": "hello"}, headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["result"] == {"msg_id": "123"}
        mock_adapters["discord"].send.assert_called_once_with("user1", "hello")

    @pytest.mark.asyncio
    async def test_channel_upload(self, app_client, auth_headers, mock_adapters):
        res = app_client.post("/api/v1/channels/discord/upload", json={"file_data": "base64...", "file_name": "test.png"}, headers=auth_headers)
        assert res.status_code == 200
        mock_adapters["discord"].upload.assert_called_once()

    @pytest.mark.asyncio
    async def test_channel_health(self, app_client, auth_headers, mock_adapters):
        res = app_client.get("/api/v1/channels/discord/health", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["is_connected"] is True
        assert res.json()["integrity"] is True

    @pytest.mark.asyncio
    async def test_channel_unread(self, app_client, auth_headers, mock_adapters):
        res = app_client.get("/api/v1/channels/discord/unread", headers=auth_headers)
        assert res.status_code == 200
        assert len(res.json()) == 1

    @pytest.mark.asyncio
    async def test_channel_social_task(self, app_client, auth_headers, mock_adapters):
        res = app_client.post("/api/v1/channels/discord/social", json={"task": "like", "params": {"id": "1"}}, headers=auth_headers)
        assert res.status_code == 200
        mock_adapters["discord"].execute_social_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_channel_enterprise_task(self, app_client, auth_headers, mock_adapters):
        res = app_client.post("/api/v1/channels/discord/enterprise", json={"task": "create_ticket", "params": {}}, headers=auth_headers)
        assert res.status_code == 200
        mock_adapters["discord"].execute_enterprise_task.assert_called_once()

class TestChannelOauthWebhooks:
    @pytest.mark.asyncio
    async def test_slack_oauth_start(self, app_client, auth_headers, mock_adapters):
        res = app_client.get("/api/v1/oauth/slack/start", headers=auth_headers)
        assert res.status_code == 200
        assert "authorize_url" in res.json()

    @pytest.mark.asyncio
    async def test_slack_webhook(self, app_client, mock_adapters):
        res = app_client.post("/api/v1/webhook/slack", json={"event": "test"}, headers={"X-Slack-Signature": "sig", "X-Slack-Request-Timestamp": "123"})
        assert res.status_code == 200
        mock_adapters["slack"].process_webhook.assert_called_once()

    @pytest.mark.asyncio
    async def test_telegram_webhook(self, app_client, mock_adapters):
        res = app_client.post("/api/v1/webhook/telegram/valid_token", json={"message": "hello"})
        assert res.status_code == 200
        mock_adapters["telegram"].process_webhook.assert_called_once()

    @pytest.mark.asyncio
    async def test_wechat_webhook_verify(self, app_client, mock_adapters):
        res = app_client.get("/api/v1/webhook/wechat?msg_signature=sig&timestamp=1&nonce=n&echostr=echo")
        assert res.status_code == 200
        assert res.text == "echostr"

class TestAgentSubscriptions:
    @pytest.mark.asyncio
    async def test_get_agent_subscriptions(self, app_client, auth_headers, temp_db_session):
        with patch("backend.routers.channels.get_session", return_value=temp_db_session):
            res = app_client.get("/api/v1/agents/agent1/subscriptions", headers=auth_headers)
            assert res.status_code == 200
            assert isinstance(res.json(), list)

    @pytest.mark.asyncio
    async def test_update_agent_subscription(self, app_client, auth_headers, temp_db_session):
        with patch("backend.routers.channels.get_session", return_value=temp_db_session):
            res = app_client.put("/api/v1/agents/agent1/subscriptions", json={"channel_id": "discord", "is_active": True}, headers=auth_headers)
            assert res.status_code == 200
            
            # Check DB
            res = app_client.get("/api/v1/agents/agent1/subscriptions", headers=auth_headers)
            assert len(res.json()) == 1
            assert res.json()[0]["channel_id"] == "discord"

    @pytest.mark.asyncio
    async def test_delete_agent_subscription(self, app_client, auth_headers, temp_db_session):
        with patch("backend.routers.channels.get_session", return_value=temp_db_session):
            # Create
            app_client.put("/api/v1/agents/agent1/subscriptions", json={"channel_id": "discord", "is_active": True}, headers=auth_headers)
            # Delete
            res = app_client.delete("/api/v1/agents/agent1/subscriptions/discord", headers=auth_headers)
            assert res.status_code == 200
            
            # Check DB
            res = app_client.get("/api/v1/agents/agent1/subscriptions", headers=auth_headers)
            assert len(res.json()) == 0

    @pytest.mark.asyncio
    async def test_other_oauth_starts(self, app_client, auth_headers, mock_adapters):
        for provider in ["instagram", "facebook", "x", "msteams"]:
            mock_adapters[provider] = MockAdapter(build_oauth_url=lambda *args, **kwargs: ("url", "ver"))
            services.channel_registry[provider] = mock_adapters[provider]
            res = app_client.get(f"/api/v1/oauth/{provider}/start", headers=auth_headers)
            assert res.status_code == 200

    @pytest.mark.asyncio
    async def test_other_webhooks(self, app_client, mock_adapters):
        for provider in ["instagram", "facebook", "whatsapp"]:
            mock_adapters[provider] = MockAdapter(verify_webhook=lambda *args, **kwargs: "challenge", verify_signature=lambda *args, **kwargs: True, process_webhook=AsyncMock(), process_webhook_event=AsyncMock())
            services.channel_registry[provider] = mock_adapters[provider]
            
            res = app_client.get(f"/api/v1/webhook/{provider}?hub.mode=subscribe&hub.verify_token=token&hub.challenge=challenge")
            assert res.status_code == 200
            
            res = app_client.post(f"/api/v1/webhook/{provider}", json={"entry": []}, headers={"X-Hub-Signature-256": "sig"})
            assert res.status_code == 200

    @pytest.mark.asyncio
    async def test_msteams_google_webhook(self, app_client, mock_adapters):
        mock_adapters["msteams"] = MockAdapter(verify_bot_activity=AsyncMock(return_value=True), process_webhook=AsyncMock())
        services.channel_registry["msteams"] = mock_adapters["msteams"]
        res = app_client.post("/api/v1/webhook/msteams", json={})
        assert res.status_code == 200

        mock_adapters["google_chat"] = MockAdapter(verify_webhook=AsyncMock(return_value=True), process_event=AsyncMock(return_value={"body": "ok"}))
        services.channel_registry["google_chat"] = mock_adapters["google_chat"]
        res = app_client.post("/api/v1/webhook/google_chat", json={})
        assert res.status_code == 200
        
    @pytest.mark.asyncio
    async def test_oauth_callback(self, app_client, mock_adapters):
        from backend.security.oauth_store import oauth_store
        await oauth_store.store_state("valid_state", {"redirect_uri": "http"})
        
        # Test valid generic fallback
        mock_adapters["signal"] = MockAdapter(handle_oauth_callback=AsyncMock())
        services.channel_registry["signal"] = mock_adapters["signal"]
        res = app_client.get("/api/v1/oauth/signal/callback?state=valid_state&code=123")
        assert res.status_code == 200
    @pytest.mark.asyncio
    async def test_channels_error_paths(self, app_client, auth_headers, mock_adapters):
        # Empty registry
        services.channel_registry.clear()
        assert app_client.get("/api/v1/channels/availability", headers=auth_headers).json() == []

        # Missing adapter 404s
        assert app_client.get("/api/v1/channels/missing/config", headers=auth_headers).status_code == 404
        assert app_client.put("/api/v1/channels/missing/config", json={}, headers=auth_headers).status_code == 404
        assert app_client.post("/api/v1/channels/missing/connect", headers=auth_headers).status_code == 404
        assert app_client.put("/api/v1/channels/missing/toggle", headers=auth_headers).status_code == 404
        assert app_client.post("/api/v1/channels/missing/send", json={"recipient": "a", "content": "b"}, headers=auth_headers).status_code == 404
        assert app_client.post("/api/v1/channels/missing/upload", json={"file_data": "a", "file_name": "b"}, headers=auth_headers).status_code == 404
        assert app_client.get("/api/v1/channels/missing/health", headers=auth_headers).status_code == 404
        assert app_client.get("/api/v1/channels/missing/unread", headers=auth_headers).status_code == 404
        assert app_client.post("/api/v1/channels/missing/social", json={"task":"a", "params":{}}, headers=auth_headers).status_code == 404
        assert app_client.post("/api/v1/channels/missing/enterprise", json={"task":"a", "params":{}}, headers=auth_headers).status_code == 404

        # 501 Unsupported Actions
        class EmptyAdapter:
            pass
        services.channel_registry["empty"] = EmptyAdapter()
        
        assert app_client.put("/api/v1/channels/empty/config", json={}, headers=auth_headers).status_code == 501
        assert app_client.post("/api/v1/channels/empty/connect", headers=auth_headers).status_code == 501
        
        # Toggle connect unsupported
        EmptyAdapter.is_connected = False
        assert app_client.put("/api/v1/channels/empty/toggle", headers=auth_headers).status_code == 501
        
        # Toggle disconnect unsupported
        EmptyAdapter.is_connected = True
        assert app_client.put("/api/v1/channels/empty/toggle", headers=auth_headers).status_code == 501
        
        assert app_client.post("/api/v1/channels/empty/upload", json={"file_data": "a", "file_name": "b"}, headers=auth_headers).status_code == 501
        assert app_client.post("/api/v1/channels/empty/social", json={"task":"a", "params":{}}, headers=auth_headers).status_code == 501
        
        assert app_client.get("/api/v1/channels/empty/unread", headers=auth_headers).json() == []

        # Send edge cases
        EmptyAdapter.is_connected = False
        services.channel_registry["discord"] = mock_adapters["discord"]
        assert app_client.post("/api/v1/channels/empty/send", json={"recipient": "a", "content": "b"}, headers=auth_headers).status_code == 503
        
        mock_adapters["discord"].is_connected = True
        assert app_client.post("/api/v1/channels/discord/send", json={"recipient": "a", "content": ""}, headers=auth_headers).status_code == 400
        
        mock_adapters["discord"].send.side_effect = Exception("Send failed")
        assert app_client.post("/api/v1/channels/discord/send", json={"recipient": "a", "content": "b"}, headers=auth_headers).status_code == 500
        
        mock_adapters["discord"].upload.side_effect = Exception("Upload failed")
        assert app_client.post("/api/v1/channels/discord/upload", json={"file_data": "a", "file_name": "b"}, headers=auth_headers).status_code == 500
        
        mock_adapters["discord"].fetch_unread.side_effect = Exception("Unread failed")
        assert app_client.get("/api/v1/channels/discord/unread", headers=auth_headers).status_code == 500

        mock_adapters["discord"].execute_social_task.side_effect = Exception("Task failed")
        assert app_client.post("/api/v1/channels/discord/social", json={"task": "a", "params": {}}, headers=auth_headers).status_code == 500
        
        mock_adapters["discord"].execute_enterprise_task.side_effect = Exception("Task failed")
        assert app_client.post("/api/v1/channels/discord/enterprise", json={"task": "a", "params": {}}, headers=auth_headers).status_code == 500

        # Health integrity exception
        mock_adapters["discord"].validate_integrity = AsyncMock(side_effect=Exception("Integrity check failed"))
        health = app_client.get("/api/v1/channels/discord/health", headers=auth_headers).json()
        assert health["integrity"] == False
        assert health["integrity_error"] == "Integrity check failed"
        
        # Social generic fallback to send
        del mock_adapters["discord"].execute_social_task
        mock_adapters["discord"].send = AsyncMock(return_value="sent")
        res = app_client.post("/api/v1/channels/discord/social", json={"task": "send", "params": {"recipient": "a", "content": "b"}}, headers=auth_headers)
        print(res.text)
        assert res.status_code == 200

        # Enterprise generic fallback to social
        del mock_adapters["discord"].execute_enterprise_task
        # Re-add social task for this test
        mock_adapters["discord"].execute_social_task = AsyncMock(return_value="social")
        assert app_client.post("/api/v1/channels/discord/enterprise", json={"task": "other", "params": {}}, headers=auth_headers).status_code == 200

    @pytest.mark.asyncio
    async def test_webhook_endpoints_error_paths(self, app_client, mock_adapters, auth_headers):
        services.channel_registry.clear()
        
        # Webhooks don't use Depends(verify_authenticated) EXCEPT for some endpoints! Wait!
        # Let's check which ones have Depends(verify_authenticated).
        # Wechat qr-init: YES
        # Wechat webhook: NO
        # Slack start: YES
        # Slack webhook: NO
        
        # Missing adapter
        assert app_client.get("/api/v1/webhook/wechat?msg_signature=1&timestamp=2&nonce=3").status_code == 503
        assert app_client.post("/api/v1/webhook/wechat?msg_signature=1&timestamp=2&nonce=3").json() == "<xml><Content>ok</Content></xml>"
        
        assert app_client.get("/api/v1/oauth/slack/start", headers=auth_headers).status_code == 503
        assert app_client.post("/api/v1/webhook/slack").status_code == 401
        
        assert app_client.get("/api/v1/webhook/whatsapp").status_code == 503
        assert app_client.post("/api/v1/webhook/whatsapp").status_code == 403
        
        assert app_client.get("/api/v1/oauth/instagram/start", headers=auth_headers).status_code == 503
        assert app_client.get("/api/v1/webhook/instagram").status_code == 503
        assert app_client.post("/api/v1/webhook/instagram").status_code == 403

        assert app_client.get("/api/v1/oauth/facebook/start", headers=auth_headers).status_code == 503
        assert app_client.get("/api/v1/webhook/facebook").status_code == 503
        assert app_client.post("/api/v1/webhook/facebook").status_code == 403

        assert app_client.get("/api/v1/oauth/x/start", headers=auth_headers).status_code == 503
        assert app_client.get("/api/v1/oauth/msteams/start", headers=auth_headers).status_code == 503
        assert app_client.post("/api/v1/webhook/msteams").status_code == 401
        
        assert app_client.post("/api/v1/webhook/google_chat").status_code == 401
        
        # Wechat signature verification failure
        mock_wechat = MockAdapter(verify_callback=MagicMock(return_value=None), process_webhook=AsyncMock())
        services.channel_registry["wechat"] = mock_wechat
        assert app_client.get("/api/v1/webhook/wechat?msg_signature=1&timestamp=2&nonce=3").status_code == 403
        assert app_client.post("/api/v1/webhook/wechat?msg_signature=1&timestamp=2&nonce=3").status_code == 403

        # Webhook verification failures
        mock_whatsapp = MockAdapter(verify_webhook=MagicMock(return_value=None), verify_signature=MagicMock(return_value=False))
        services.channel_registry["whatsapp"] = mock_whatsapp
        assert app_client.get("/api/v1/webhook/whatsapp").status_code == 403
        assert app_client.post("/api/v1/webhook/whatsapp").status_code == 403
        
        mock_instagram = MockAdapter(verify_webhook=MagicMock(return_value=None), verify_signature=MagicMock(return_value=False))
        services.channel_registry["instagram"] = mock_instagram
        assert app_client.get("/api/v1/webhook/instagram").status_code == 403
        assert app_client.post("/api/v1/webhook/instagram").status_code == 403

        mock_facebook = MockAdapter(verify_webhook=MagicMock(return_value=None), verify_signature=MagicMock(return_value=False))
        services.channel_registry["facebook"] = mock_facebook
        assert app_client.get("/api/v1/webhook/facebook").status_code == 403
        assert app_client.post("/api/v1/webhook/facebook").status_code == 403
        
        # Valid signature returning false
        mock_msteams = MockAdapter(verify_bot_activity=AsyncMock(return_value=False))
        services.channel_registry["msteams"] = mock_msteams
        assert app_client.post("/api/v1/webhook/msteams").status_code == 401
        
        mock_google_chat = MockAdapter(verify_webhook=AsyncMock(return_value=False))
        services.channel_registry["google_chat"] = mock_google_chat
        assert app_client.post("/api/v1/webhook/google_chat").status_code == 401

    @pytest.mark.asyncio
    async def test_specialized_channel_routes(self, app_client, auth_headers, mock_adapters):
        services.channel_registry.clear()
        # Missing adapter
        assert app_client.post("/api/v1/channels/iphone/pair", json={"cert": "123"}, headers=auth_headers).status_code == 503
        assert app_client.post("/api/v1/channels/webchat/launch", json={"url": "abc"}, headers=auth_headers).status_code == 501
        assert app_client.post("/api/v1/channels/icloud/2fa", json={"code": "123"}, headers=auth_headers).status_code == 501
        assert app_client.post("/api/v1/channels/webchat/session/abc/capture", json={}, headers=auth_headers).status_code == 501
        
        # iWatch
        assert app_client.get("/api/v1/channels/iwatch/status", headers=auth_headers).json() == {"status": "unloaded"}
        assert app_client.get("/api/v1/channels/iwatch/pairing-qr", headers=auth_headers).status_code == 503
        
        # Note: /api/v1/channels/iwatch/pair doesn't have Depends(verify_authenticated) in the source! Wait, it doesn't?
        # Let's check channels.py line 291: @router.post("/channels/iwatch/pair") - No Depends!
        assert app_client.post("/api/v1/channels/iwatch/pair", json={"code": "123"}, headers=auth_headers).status_code == 503
        
        # Add iWatch mock to test 400
        services.channel_registry["iwatch"] = mock_adapters["discord"]
        assert app_client.post("/api/v1/channels/iwatch/pair", json={"code": "123"}, headers=auth_headers).status_code == 400
        
        # biometrics doesn't have Depends(verify_authenticated) but HAS CsrfProtect
        mock_adapters["discord"].verify_device_token = MagicMock(return_value="dev_1")
        mock_adapters["discord"].ingest_telemetry = AsyncMock()
        assert app_client.post("/api/v1/channels/iwatch/biometrics", json={"hr": 70}, headers=auth_headers).status_code == 200
        
        mock_adapters["discord"].get_recent_telemetry = MagicMock(return_value=[])
        assert app_client.get("/api/v1/channels/iwatch/telemetry", headers=auth_headers).status_code == 200
        
        # iphone pair failure
        mock_iphone = MockAdapter(store_pinned_ca=AsyncMock(return_value=False))
        services.channel_registry["iphone"] = mock_iphone
        assert app_client.post("/api/v1/channels/iphone/pair", json={}, headers=auth_headers).status_code == 400
        assert app_client.post("/api/v1/channels/iphone/pair", json={"cert": "123"}, headers=auth_headers).status_code == 500
        
        # Webchat
        mock_webchat = MockAdapter(launch_browser=AsyncMock(return_value={}), capture_session=AsyncMock(return_value={}))
        services.channel_registry["webchat"] = mock_webchat
        assert app_client.post("/api/v1/channels/webchat/launch", json={}, headers=auth_headers).status_code == 400
        assert app_client.post("/api/v1/channels/webchat/launch", json={"url": "abc"}, headers=auth_headers).status_code == 200
        assert app_client.post("/api/v1/channels/webchat/session/abc/capture", json={}, headers=auth_headers).status_code == 200
        
        mock_icloud = MockAdapter(submit_2fa=AsyncMock(return_value={}))
        services.channel_registry["icloud"] = mock_icloud
        assert app_client.post("/api/v1/channels/icloud/2fa", json={"code": "123"}, headers=auth_headers).status_code == 200

        # Delete agent subscription missing
        res = app_client.delete("/api/v1/agents/a1/subscriptions/c1", headers=auth_headers)
        assert res.status_code == 404
