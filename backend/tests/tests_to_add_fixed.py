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
        mock_adapters["discord"].execute_social_task = None
        mock_adapters["discord"].send = AsyncMock(return_value="sent")
        assert app_client.post("/api/v1/channels/discord/social", json={"task": "send", "params": {"recipient": "a", "content": "b"}}, headers=auth_headers).status_code == 200

        # Enterprise generic fallback to social
        mock_adapters["discord"].execute_enterprise_task = None
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
        assert app_client.post("/api/v1/webhook/wechat?msg_signature=1&timestamp=2&nonce=3").text == "<xml><Content>ok</Content></xml>"
        
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
        assert app_client.post("/api/v1/channels/iwatch/pair", json={"code": "123"}).status_code == 400
        
        # biometrics doesn't have Depends(verify_authenticated) either!
        assert app_client.post("/api/v1/channels/iwatch/biometrics", json={"hr": 70}).status_code == 503
        
        assert app_client.get("/api/v1/channels/iwatch/telemetry", headers=auth_headers).status_code == 503
        
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
