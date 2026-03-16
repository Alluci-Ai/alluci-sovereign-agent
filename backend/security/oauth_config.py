# backend/security/oauth_config.py
"""
OAuth 2.0 provider configuration registry.
Keys MUST match the channel_id strings used throughout the app:
slack, gmail, gdrive, discord, instagram, facebook, msteams, twitter
"""
from typing import Dict, Any, Optional

OAUTH_CONFIG: Dict[str, Dict[str, Any]] = {
    "slack": {
        "client_id_env": "SLACK_CLIENT_ID",
        "client_secret_env": "SLACK_CLIENT_SECRET",
        "auth_url": "https://slack.com/oauth/v2/authorize",
        "token_url": "https://slack.com/api/oauth.v2.access",
        "scopes": ["channels:read", "chat:write", "im:history", "im:write",
                   "users:read", "channels:history", "groups:history"],
        "redirect_path": "/api/v1/channels/slack/callback",
        "pkce": False,
    },
    "gmail": {
        "client_id_env": "GOOGLE_CLIENT_ID",
        "client_secret_env": "GOOGLE_CLIENT_SECRET",
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": [
            "openid", "email", "profile",
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/gmail.send",
        ],
        "extra_params": {"access_type": "offline", "prompt": "consent"},
        "redirect_path": "/api/v1/channels/gmail/callback",
        "pkce": False,
    },
    "gdrive": {
        "client_id_env": "GOOGLE_CLIENT_ID",
        "client_secret_env": "GOOGLE_CLIENT_SECRET",
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": [
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive.metadata.readonly",
        ],
        "extra_params": {"access_type": "offline", "prompt": "consent"},
        "redirect_path": "/api/v1/channels/gdrive/callback",
        "pkce": False,
    },
    "discord": {
        "client_id_env": "DISCORD_CLIENT_ID",
        "client_secret_env": "DISCORD_CLIENT_SECRET",
        "auth_url": "https://discord.com/api/oauth2/authorize",
        "token_url": "https://discord.com/api/oauth2/token",
        "scopes": ["identify", "guilds", "bot", "messages.read"],
        "redirect_path": "/api/v1/channels/discord/callback",
        "pkce": False,
    },
    "instagram": {
        "client_id_env": "INSTAGRAM_CLIENT_ID",
        "client_secret_env": "INSTAGRAM_CLIENT_SECRET",
        "auth_url": "https://www.facebook.com/v20.0/dialog/oauth",
        "token_url": "https://graph.facebook.com/v20.0/oauth/access_token",
        "scopes": [
            "instagram_basic", "instagram_manage_messages",
            "pages_messaging", "pages_show_list", "pages_manage_metadata",
        ],
        "redirect_path": "/api/v1/channels/instagram/callback",
        "pkce": False,
    },
    "facebook": {
        "client_id_env": "FACEBOOK_CLIENT_ID",
        "client_secret_env": "FACEBOOK_CLIENT_SECRET",
        "auth_url": "https://www.facebook.com/v20.0/dialog/oauth",
        "token_url": "https://graph.facebook.com/v20.0/oauth/access_token",
        "scopes": [
            "pages_messaging", "pages_show_list",
            "pages_read_engagement", "pages_manage_metadata",
        ],
        "redirect_path": "/api/v1/channels/facebook/callback",
        "pkce": False,
    },
    "msteams": {
        "client_id_env": "MSTEAMS_CLIENT_ID",
        "client_secret_env": "MSTEAMS_CLIENT_SECRET",
        "auth_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "scopes": [
            "https://graph.microsoft.com/Chat.ReadWrite",
            "https://graph.microsoft.com/ChannelMessage.Send",
            "https://graph.microsoft.com/User.Read",
            "offline_access",
        ],
        "redirect_path": "/api/v1/channels/msteams/callback",
        "pkce": False,
    },
    "twitter": {
        "client_id_env": "TWITTER_CLIENT_ID",
        "client_secret_env": "TWITTER_CLIENT_SECRET",
        "auth_url": "https://twitter.com/i/oauth2/authorize",
        "token_url": "https://api.twitter.com/2/oauth2/token",
        "scopes": [
            "tweet.read", "tweet.write",
            "dm.read", "dm.write",
            "users.read", "offline.access",
        ],
        "redirect_path": "/api/v1/channels/twitter/callback",
        "pkce": True,  # X requires PKCE
    },
}


def get_provider_config(provider_id: str) -> Optional[Dict[str, Any]]:
    """Returns config for a provider by its full ID. Returns None if not found."""
    # Support alias: 'x' → 'twitter'
    if provider_id == "x":
        provider_id = "twitter"
    return OAUTH_CONFIG.get(provider_id)


def get_client_credentials(provider_id: str) -> tuple[Optional[str], Optional[str]]:
    """Returns (client_id, client_secret) from environment for a given provider."""
    import os
    cfg = get_provider_config(provider_id)
    if not cfg:
        return None, None
    client_id = os.getenv(cfg["client_id_env"])
    client_secret = os.getenv(cfg.get("client_secret_env", ""))
    return client_id, client_secret
