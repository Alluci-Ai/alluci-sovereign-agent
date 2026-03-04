const { Client, GatewayIntentBits, Partials, EmbedBuilder, REST, Routes } = require('discord.js');
const fs = require('fs');
const path = require('path');

function sendEvent(method, params = {}) {
    process.stdout.write(JSON.stringify({ jsonrpc: "2.0", method, params }) + '\n');
}

function log(...args) {
    process.stderr.write(`[DS_SIDECAR] ${args.join(' ')}\n`);
}

const bridgeId = process.argv[2] || 'discord';
const vaultPath = process.argv[3] || path.join(process.env.HOME, '.polytope', 'vaults', 'discord');

log(`Initializing Discord sidecar... Bridge: ${bridgeId}, Vault: ${vaultPath}`);

const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent,
        GatewayIntentBits.GuildMembers,
        GatewayIntentBits.DirectMessages
    ],
    partials: [Partials.Channel, Partials.Message]
});

let botToken = null;

client.on('ready', async () => {
    log(`Discord Bot Logged in as ${client.user.tag}!`);

    // Fetch Guilds & Channels
    const guildData = [];
    for (const [id, guild] of client.guilds.cache) {
        const channels = await guild.channels.fetch();
        guildData.push({
            id: guild.id,
            name: guild.name,
            channels: channels.filter(c => c.type === 0).map(c => ({ id: c.id, name: c.name })) // 0: GuildText
        });
    }

    sendEvent('ready', {
        user: {
            id: client.user.id,
            tag: client.user.tag,
            username: client.user.username
        },
        guilds: guildData
    });
});

client.on('messageCreate', async (message) => {
    if (message.author.bot) return;

    log(`Message from ${message.author.tag} in ${message.guild ? message.guild.name : 'DM'}: ${message.content}`);

    const payload = {
        id: message.id,
        from: message.author.id,
        author: {
            id: message.author.id,
            username: message.author.username,
            tag: message.author.tag
        },
        channel_id: message.channel.id,
        guild_id: message.guildId,
        content: message.content,
        timestamp: message.createdAt.toISOString(),
        protocol: 'DISCORD'
    };

    // Attachments
    if (message.attachments.size > 0) {
        payload.attachments = message.attachments.map(a => ({
            url: a.url,
            name: a.name,
            contentType: a.contentType
        }));
    }

    sendEvent('message', { msg: payload });
});

client.on('interactionCreate', async (interaction) => {
    if (!interaction.isChatInputCommand()) return;

    log(`Slash command from ${interaction.user.tag}: /${interaction.commandName}`);

    const payload = {
        id: interaction.id,
        type: 'INTERACTION',
        command: interaction.commandName,
        options: interaction.options.data,
        user: interaction.user.username,
        user_id: interaction.user.id,
        guild_id: interaction.guildId,
        channel_id: interaction.channelId,
        protocol: 'DISCORD',
        timestamp: new Date().toISOString()
    };

    // Acknowledge interaction (essential to avoid expiration)
    // We send it to Python first, but we might want to defer the reply.
    // However, most Polytope interactions will be responded to via a normal message later.
    // For now, let's just acknowledge with a "Thinking..." or similar if needed.
    // Actually, let's keep it simple and just send the event to Python.

    sendEvent('interaction', { interaction: payload });

    try {
        await interaction.reply({ content: "⏳ Processing objective through Sovereign OS...", ephemeral: true });
    } catch (e) {
        log("Interaction reply failed (expected if handled fast):", e);
    }
});

process.stdin.on('data', async (byteData) => {
    try {
        const lines = byteData.toString().split('\n').filter(l => l.trim());
        for (const line of lines) {
            const req = JSON.parse(line);
            if (req.method === 'login') {
                botToken = req.params.token;
                log('Attempting login with token...');
                client.login(botToken).catch(err => {
                    log('Login error:', err);
                    sendEvent('status', { state: 'ERROR', message: err.message });
                });
            } else if (req.method === 'send_message') {
                const { to, body, embeds } = req.params;
                const channel = await client.channels.fetch(to);
                if (channel) {
                    const sendPayload = { content: body || "" };
                    if (embeds && embeds.length > 0) {
                        sendPayload.embeds = embeds.map(e => new EmbedBuilder(e));
                    }
                    const res = await channel.send(sendPayload);
                    sendEvent('response', { id: req.id, status: 'success', messageId: res.id });
                } else {
                    sendEvent('response', { id: req.id, status: 'failed', error: 'Channel not found' });
                }
            } else if (req.method === 'register_commands') {
                const { guild_id, commands } = req.params;
                if (!botToken || !client.user) {
                    sendEvent('response', { id: req.id, status: 'failed', error: 'Not logged in' });
                    continue;
                }
                const rest = new REST().setToken(botToken);
                try {
                    log(`Registering ${commands.length} commands for guild ${guild_id}`);
                    await rest.put(
                        Routes.applicationGuildCommands(client.user.id, guild_id),
                        { body: commands }
                    );
                    sendEvent('response', { id: req.id, status: 'success' });
                } catch (error) {
                    log('Register commands error:', error);
                    sendEvent('response', { id: req.id, status: 'failed', error: error.message });
                }
            }
        }
    } catch (e) {
        log('RPC Error:', e);
    }
});
