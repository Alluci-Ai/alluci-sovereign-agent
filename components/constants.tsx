
import { Connection, AutonomyLevel } from '../types';

export const KNOWN_PROVIDERS = {
    llm: [
        { id: 'openai', label: 'OpenAI' },
        { id: 'anthropic', label: 'Anthropic' },
        { id: 'googleCloud', label: 'Google Cloud' },
        { id: 'groq', label: 'Groq' },
        { id: 'deepseek', label: 'DeepSeek' }
    ],
    audio: [
        { id: 'openaiRealtime', label: 'OpenAI Realtime API' },
        { id: 'elevenLabsAgents', label: 'ElevenLabs' },
        { id: 'retellAi', label: 'Retell AI' },
        { id: 'inworldAi', label: 'Inworld AI' }
    ],
    music: [
        { id: 'suno', label: 'Suno API' },
        { id: 'elevenLabsMusic', label: 'ElevenLabs Music API' },
        { id: 'stableAudio', label: 'Stable Audio' },
        { id: 'soundverse', label: 'Soundverse' },
        { id: 'udio', label: 'Udio' },
        { id: 'googleLyria', label: 'Google' }
    ],
    image: [
        { id: 'openaiDalle', label: 'OpenAI' },
        { id: 'falAi', label: 'Fal.ai' },
        { id: 'midjourney', label: 'Midjourney' },
        { id: 'adobeFirefly', label: 'Adobe Firefly API' },
        { id: 'googleNanoBanana', label: 'Google' },
        { id: 'seedance', label: 'Seedance 2.0' }
    ],
    video: [
        { id: 'runway', label: 'Runway' },
        { id: 'luma', label: 'Luma Dream Machine' },
        { id: 'heygen', label: 'HeyGen / Synthesia' },
        { id: 'livepeer', label: 'Livepeer' },
        { id: 'googleVeo', label: 'Google' },
        { id: 'googleGenie', label: 'Google' }
    ]
};

export const validateApiKey = (provider: string, key: string): boolean => {
    if (!key) return true;
    const k = key.trim();
    if (k.length < 8) return false;

    if (provider.startsWith('openai')) return k.startsWith('sk-');
    if (provider.startsWith('google')) return k.startsWith('AIza');
    if (provider.startsWith('elevenLabs')) return /^[a-fA-F0-9]{32}$/.test(k) || k.startsWith('sk_');

    switch (provider) {
        case 'anthropic': return k.startsWith('sk-ant');
        case 'groq': return k.startsWith('gsk_');
        case 'deepseek': return k.startsWith('sk-');
        case 'retellAi': return k.startsWith('key_');
        case 'falAi': return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(k) || k.startsWith('key-');
        case 'runway': return k.startsWith('runway_') || k.length > 25;
        case 'stableAudio': return k.length > 30;
        case 'livepeer': return k.length > 20;
        case 'adobeFirefly': return k.startsWith('ec_') || k.length > 20;
        case 'inworldAi': return k.length > 30;
        case 'heygen': return k.length > 20;
        default: return k.length > 15;
    }
};

export const INITIAL_CONNECTIONS: Connection[] = [
    { id: 'icloud', name: 'iCloud', status: 'DISCONNECTED', type: 'WORKSPACE', authType: 'TOKEN', autonomyLevel: AutonomyLevel.RESTRICTED, isEncrypted: false },
    { id: 'email', name: 'iCloud Email', status: 'DISCONNECTED', type: 'WORKSPACE', authType: 'TOKEN', autonomyLevel: AutonomyLevel.RESTRICTED, isEncrypted: true },
    { id: 'imessage', name: 'iMessage', status: 'DISCONNECTED', type: 'MESSAGING', authType: 'MACOS_PERMS', autonomyLevel: AutonomyLevel.RESTRICTED, isEncrypted: true },
    { id: 'iwatch', name: 'iWatch', status: 'DISCONNECTED', type: 'MESSAGING', authType: 'SECURE_TUNNEL', autonomyLevel: AutonomyLevel.RESTRICTED, isEncrypted: true },
    { id: 'iphone', name: 'iPhone', status: 'DISCONNECTED', type: 'MESSAGING', authType: 'SECURE_TUNNEL', autonomyLevel: AutonomyLevel.RESTRICTED, isEncrypted: true },
    { id: 'wa', name: 'WhatsApp', status: 'DISCONNECTED', type: 'MESSAGING', authType: 'QR_SYNC', autonomyLevel: AutonomyLevel.RESTRICTED, isEncrypted: true },
    { id: 'tg', name: 'Telegram', status: 'DISCONNECTED', type: 'MESSAGING', authType: 'TOKEN', autonomyLevel: AutonomyLevel.RESTRICTED, isEncrypted: true },
    { id: 'dc', name: 'Discord', status: 'DISCONNECTED', type: 'MESSAGING', authType: 'OAUTH2', autonomyLevel: AutonomyLevel.RESTRICTED, isEncrypted: true },
    { id: 'sg', name: 'Signal', status: 'DISCONNECTED', type: 'MESSAGING', authType: 'TOKEN', autonomyLevel: AutonomyLevel.RESTRICTED, isEncrypted: true },
    { id: 'ig', name: 'Instagram', status: 'DISCONNECTED', type: 'MESSAGING', authType: 'OAUTH2', autonomyLevel: AutonomyLevel.RESTRICTED, isEncrypted: true },
    { id: 'fb', name: 'Facebook', status: 'DISCONNECTED', type: 'MESSAGING', authType: 'OAUTH2', autonomyLevel: AutonomyLevel.RESTRICTED, isEncrypted: true },
    { id: 'x', name: 'X', status: 'DISCONNECTED', type: 'MESSAGING', authType: 'OAUTH2', autonomyLevel: AutonomyLevel.RESTRICTED, isEncrypted: true },
    { id: 'sl', name: 'Slack', status: 'DISCONNECTED', type: 'MESSAGING', authType: 'TOKEN', autonomyLevel: AutonomyLevel.RESTRICTED, isEncrypted: true },
    { id: 'mt', name: 'MS Teams', status: 'DISCONNECTED', type: 'WORKSPACE', authType: 'OAUTH2', autonomyLevel: AutonomyLevel.RESTRICTED, isEncrypted: true },
    { id: 'webchat', name: 'WebChat', status: 'DISCONNECTED', type: 'MESSAGING', authType: 'WEB_SESSION', autonomyLevel: AutonomyLevel.RESTRICTED, isEncrypted: false },
    { id: 'wechat', name: 'WeChat', status: 'DISCONNECTED', type: 'MESSAGING', authType: 'QR_SYNC', autonomyLevel: AutonomyLevel.RESTRICTED, isEncrypted: true },
    { id: 'gm', name: 'Gmail', status: 'DISCONNECTED', type: 'WORKSPACE', authType: 'OAUTH2', autonomyLevel: AutonomyLevel.RESTRICTED, isEncrypted: true },
    { id: 'gd', name: 'G-Drive', status: 'DISCONNECTED', type: 'WORKSPACE', authType: 'OAUTH2', autonomyLevel: AutonomyLevel.RESTRICTED, isEncrypted: true },
    { id: 'notion', name: 'Notion', status: 'DISCONNECTED', type: 'WORKSPACE', authType: 'TOKEN', autonomyLevel: AutonomyLevel.RESTRICTED, isEncrypted: true },
    { id: 'github', name: 'GitHub', status: 'DISCONNECTED', type: 'WORKSPACE', authType: 'TOKEN', autonomyLevel: AutonomyLevel.RESTRICTED, isEncrypted: true },
    { id: 'verus', name: 'VerusID', status: 'DISCONNECTED', type: 'WORKSPACE', authType: 'IDENTITY_LINK', autonomyLevel: AutonomyLevel.SOVEREIGN, isEncrypted: true }
];
