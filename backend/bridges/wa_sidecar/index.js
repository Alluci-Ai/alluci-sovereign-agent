const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const qrcode = require('qrcode');
const fs = require('fs');
const path = require('path');

// Communication with Python via JSON-RPC over stdio
function sendEvent(method, params = {}) {
    process.stdout.write(JSON.stringify({ jsonrpc: "2.0", method, params }) + '\n');
}

// Read and log to stderr to avoid polluting stdout (which is used for RPC)
function log(...args) {
    process.stderr.write(`[WA_SIDECAR] ${args.join(' ')}\n`);
}

// Arguments from Python: bridge_id, vault_path
const bridgeId = process.argv[2] || 'whatsapp';
const vaultPath = process.argv[3] || path.join(process.env.HOME, '.polytope', 'vaults', 'whatsapp');
const sessionDataPath = path.join(vaultPath, '.wwebjs_auth');

log(`Initializing WhatsApp sidecar... Bridge: ${bridgeId}, Auth Path: ${sessionDataPath}`);

const client = new Client({
    authStrategy: new LocalAuth({
        clientId: bridgeId,
        dataPath: sessionDataPath
    }),
    puppeteer: {
        args: ['--no-sandbox', '--disable-setuid-sandbox'],
        executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || null // Allow override
    }
});

client.on('qr', (qr) => {
    log('QR received, generating base64...');
    qrcode.toDataURL(qr, (err, url) => {
        if (err) {
            log('Error generating QR base64:', err);
            return;
        }
        sendEvent('qr', { qr: url });
    });
});

client.on('ready', () => {
    log('Client is ready!');
    sendEvent('ready', {
        info: client.info,
        wid: client.info.wid._serialized,
        pushname: client.info.pushname
    });
});

client.on('authenticated', () => {
    log('Authenticated successfully');
});

client.on('auth_failure', (msg) => {
    log('Authentication failure:', msg);
    sendEvent('auth_failure', { message: msg });
});

client.on('disconnected', (reason) => {
    log('Disconnected:', reason);
    sendEvent('status', { state: 'DISCONNECTED', reason });
});

client.on('change_state', (state) => {
    log('State change:', state);
    sendEvent('status', { state: state });
});

client.on('message', async (msg) => {
    // Only handle private chats (no groups for now)
    if (msg.from.includes('@g.us')) return;

    log(`Message received from ${msg.from}: ${msg.type}`);

    const payload = {
        id: msg.id.id,
        from: msg.from,
        timestamp: msg.timestamp,
        type: msg.type,
        body: msg.body,
        from_name: msg._data.notifyName || 'unknown'
    };

    if (msg.hasMedia) {
        try {
            const media = await msg.downloadMedia();
            if (media) {
                payload.media = {
                    mimetype: media.mimetype,
                    data: media.data,
                    filename: media.filename
                };
            }
        } catch (e) {
            log('Error downloading media:', e);
        }
    }

    sendEvent('message', { msg: payload });
});

process.stdin.on('data', async (data) => {
    try {
        const lines = data.toString().split('\n').filter(l => l.trim());
        for (const line of lines) {
            const req = JSON.parse(line);
            if (req.method === 'send_message') {
                const { to, body } = req.params;
                log(`Sending text to ${to}`);
                const res = await client.sendMessage(to, body);
                sendEvent('response', { id: req.id, status: 'success', messageId: res.id.id });
            } else if (req.method === 'send_media') {
                const { to, mimetype, data: b64, filename, caption } = req.params;
                log(`Sending media to ${to}`);
                const media = new MessageMedia(mimetype, b64, filename);
                const res = await client.sendMessage(to, media, { caption });
                sendEvent('response', { id: req.id, status: 'success', messageId: res.id.id });
            }
        }
    } catch (e) {
        log('Error processing input command:', e);
    }
});

client.initialize();
