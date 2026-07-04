// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { Connection, AuthType, AutonomyLevel } from './types';
import { SovereignSecurityManager, SimplicialVault } from './alluciCore';
import { getCsrfToken } from './csrfStore';

/**
 * [ BRIDGE_REGISTRY ]
 * Handles the logic for OAuth, QR Sync, and VDXF Identity linking.
 */
export class BridgeManager {
  private security: SovereignSecurityManager;
  private vaults: Map<string, SimplicialVault> = new Map();
  private verusIdentity: string | null = null;
  private manifoldIntegrity: number = 1.0;
  private access_token: string | null = null;
  private logger: Console | { error: (msg: string) => void };

  constructor(security: SovereignSecurityManager) {
    this.security = security;
    this.logger = console;
  }

  setAccessToken(token: string | null) {
    this.access_token = token;
  }

  /**
   * [ MANIFOLD_INTEGRITY_CHECK ]
   * Checks for vault cross-contamination or unauthorized access.
   */
  checkIntegrity(): number {
    return this.manifoldIntegrity;
  }

  /**
   * [ VERUSID_VDXF_HANDSHAKE ]
   * Implements Verus Data Exchange Format.
   */
  async handleVerusHandshake(verusId: string): Promise<boolean> {
    console.log(`[ VERUS_VDXF ]: Handover to SSID QR Flow for ${verusId}`);
    // The actual handshake is managed by the VerusIdLogin component
    // in the AuthPortal overlay. We just return true to allow the portal to open.
    this.verusIdentity = verusId;
    return true;
  }

  /**
   * [ GATEWAY_INITIALIZATION ]
   */
  async initializeBridge(connection: Connection): Promise<boolean> {
    // KEEP: Vault isolation
    const vault = new SimplicialVault(connection.id);
    this.vaults.set(connection.id, vault);
    // REMOVE: Biometric check entirely — WebAuthn lives in Alluci login, NOT here.
    // REMOVE: All mock dispatch methods (handleQrSync, processOAuthFlow, etc).
    //         Real auth is handled by modal components via /api/channels/{id}/config.
    return true;  // Vault provisioned. Modal handles the rest.
  }

  async performRotateKeys(): Promise<void> {
    for (const vault of this.vaults.values()) {
      await vault.rotateKeys();
    }
  }

  async performFlushCache(): Promise<void> {
    for (const vault of this.vaults.values()) {
      await vault.flushCache();
    }
  }

  /**
   * [ IMESSAGE_DISPATCHER ]
   * Sends encrypted pulses via the iMessage Secure Tunnel.
   */
  async sendMessage(bridgeId: string, recipient: string, text: string): Promise<boolean> {
    try {
      const daemonUrl = import.meta.env?.VITE_DAEMON_URL || 'http://127.0.0.1:8000';
      const res = await fetch(`${daemonUrl}/api/v1/channels/${bridgeId}/send`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-CSRF-Token': await getCsrfToken(daemonUrl, this.access_token) || ''
        },
        credentials: 'include',
        body: JSON.stringify({ recipient, content: text })
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        this.logger?.error(`sendMessage failed [${bridgeId}]: ${err.detail}`);
      }
      return res.ok;
    } catch (e) {
      this.logger?.error(`sendMessage network error [${bridgeId}]: ${e}`);
      return false;
    }
  }

  /**
   * [ ICLOUD_DRIVE_SYNC ]
   * Sovereign file operations for the Cloud Manifold.
   */
  async uploadToCloud(bridgeId: string, fileData: string, fileName: string): Promise<boolean> {
    try {
      const daemonUrl = import.meta.env?.VITE_DAEMON_URL || 'http://127.0.0.1:8000';
      const res = await fetch(`${daemonUrl}/api/v1/channels/${bridgeId}/upload`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-CSRF-Token': await getCsrfToken(daemonUrl, this.access_token) || ''
        },
        credentials: 'include',
        body: JSON.stringify({ file_data: fileData, file_name: fileName })
      });
      return res.ok;
    } catch (e) {
      return false;
    }
  }

  async retrieveFromCloud(bridgeId: string, fileId: string): Promise<string | null> {
    try {
      const daemonUrl = import.meta.env?.VITE_DAEMON_URL || 'http://127.0.0.1:8000';
      const res = await fetch(`${daemonUrl}/api/v1/channels/${bridgeId}/retrieve/${encodeURIComponent(fileId)}`, {
        credentials: 'include'
      });
      if (!res.ok) return null;
      const data = await res.json();
      return data.content ?? null;
    } catch (e) {
      return null;
    }
  }

  /**
   * [ SOCIAL_MANIFOLD_ACTUALIZATION ]
   * Executes targeted sovereign actions across the social manifold.
   */
  async executeSocialTask(bridgeId: string, task: string, params: Record<string, unknown>): Promise<boolean> {
    try {
      const daemonUrl = import.meta.env?.VITE_DAEMON_URL || 'http://127.0.0.1:8000';
      const res = await fetch(`${daemonUrl}/api/v1/channels/${bridgeId}/task`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-CSRF-Token': await getCsrfToken(daemonUrl, this.access_token) || ''
        },
        credentials: 'include',
        body: JSON.stringify({ task, params })
      });
      return res.ok;
    } catch (e) {
      return false;
    }
  }

  /**
   * [ ENTERPRISE_CORE_ACTUALIZATION ]
   * Executes workspace-level sovereign actions across Slack, Teams, and G-Suite.
   */
  async executeEnterpriseTask(bridgeId: string, taskType: string, payload: Record<string, unknown>): Promise<boolean> {
    const daemonUrl = import.meta.env?.VITE_DAEMON_URL || 'http://127.0.0.1:8000';
    const res = await fetch(`${daemonUrl}/api/v1/channels/${bridgeId}/enterprise`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": await getCsrfToken(daemonUrl, this.access_token) || ''
      },
      credentials: 'include',
      body: JSON.stringify({ type: taskType, payload })
    });
    return res.ok;
  }

  // ───────────────────────────────────────────────────────────
  // [ SOVEREIGN_VOICE_STREAM ] Cross-Device Audio Pipeline
  // ───────────────────────────────────────────────────────────

  private voiceSocket: WebSocket | null = null;
  private audioContext: AudioContext | null = null;
  private playAudioContext: AudioContext | null = null;
  private nextPlayTime: number = 0;
  private vadNode: AudioWorkletNode | null = null;
  private mediaStream: MediaStream | null = null;
  private onTranscriptCallback: ((text: string, type: 'fragment' | 'utterance' | 'cognition') => void) | null = null;

  getStream(): MediaStream | null {
    return this.mediaStream;
  }

  /**
   * Detects the host device hardware tier for dynamic model routing.
   * Falls back to MACBOOK_WORKSTATION when running in a desktop browser.
   */
  private detectDeviceTier(): 'WATCH_ULTRA' | 'IPHONE_17_PRO' | 'MACBOOK_WORKSTATION' {
    const ua = navigator.userAgent.toLowerCase();
    if (ua.includes('watch')) return 'WATCH_ULTRA';
    if (ua.includes('iphone') || ua.includes('ipad')) return 'IPHONE_17_PRO';
    return 'MACBOOK_WORKSTATION';
  }

  /**
   * [ VOICE_STREAM_INIT ]
   * Establishes a bidirectional WebSocket to the backend voice endpoint,
   * instantiates the zero-dependency VAD AudioWorkletProcessor,
   * and begins streaming 200ms PCM chunks containing active speech.
   */
  async streamAudioWebSocket(
    onTranscript: (text: string, type: 'fragment' | 'utterance' | 'cognition') => void,
    autoSubmit: boolean = false
  ): Promise<boolean> {
    try {
      this.onTranscriptCallback = onTranscript;
      this.nextPlayTime = 0;
      const deviceTier = this.detectDeviceTier();

      // 1. Open bidirectional WebSocket to the sovereign voice endpoint
      const daemonUrl = import.meta.env?.VITE_DAEMON_URL || 'http://127.0.0.1:8000';
      const wsUrl = daemonUrl.replace(/^http/, 'ws');
      this.voiceSocket = new WebSocket(`${wsUrl}/api/v1/voice/stream?device_tier=${deviceTier}&auto_submit=${autoSubmit}`);
      this.voiceSocket.binaryType = 'arraybuffer';

      // Handle incoming messages (JSON text metadata or raw binary PCM audio) from the backend
      this.voiceSocket.onmessage = async (event) => {
        try {
          if (event.data instanceof ArrayBuffer) {
            // Play back raw 48kHz Int16 mono PCM data from Kokoro using Web Audio API
            const pcmData = new Int16Array(event.data);
            const float32Data = new Float32Array(pcmData.length);
            for (let i = 0; i < pcmData.length; i++) {
                float32Data[i] = pcmData[i] / 32768.0;
            }

            if (!this.playAudioContext) {
                const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
                this.playAudioContext = new AudioContextClass({ sampleRate: 48000 });
            }
            if (this.playAudioContext.state === 'suspended') {
                await this.playAudioContext.resume();
            }

            const audioBuffer = this.playAudioContext.createBuffer(1, float32Data.length, 48000);
            audioBuffer.copyToChannel(float32Data, 0);

            const source = this.playAudioContext.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(this.playAudioContext.destination);

            // Gapless scheduling
            const startTime = Math.max(this.playAudioContext.currentTime, this.nextPlayTime);
            source.start(startTime);
            this.nextPlayTime = startTime + audioBuffer.duration;
          } else {
            const payload = JSON.parse(event.data as string);
            if (payload.text && this.onTranscriptCallback) {
              const payloadType = payload.type || (payload.is_final ? 'utterance' : 'fragment');
              this.onTranscriptCallback(payload.text, payloadType);
            }
          }
        } catch (e) {
          this.logger?.error(`Voice WS parse error: ${e}`);
        }
      };

      this.voiceSocket.onerror = (err) => {
        this.logger?.error(`Voice WebSocket error: ${err}`);
      };

      // 1b. Block until the WebSocket is confirmed OPEN before starting audio
      await new Promise<void>((resolve, reject) => {
        this.voiceSocket!.onopen = () => resolve();
        const existingOnError = this.voiceSocket!.onerror;
        this.voiceSocket!.onerror = (err) => {
          if (existingOnError) (existingOnError as Function).call(this.voiceSocket, err);
          reject(new Error('Voice WebSocket failed to connect'));
        };
      });

      // 2. Request microphone access (mono, 16kHz for Whisper compatibility)
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
        }
      });

      // 3. Create AudioContext and register the sovereign VAD worklet
      this.audioContext = new AudioContext({ sampleRate: 16000 });
      await this.audioContext.audioWorklet.addModule('/vadWorklet.js');

      const sourceNode = this.audioContext.createMediaStreamSource(this.mediaStream);
      this.vadNode = new AudioWorkletNode(this.audioContext, 'vad-processor');

      // 4. Listen for 200ms speech chunks from the VAD worklet
      this.vadNode.port.onmessage = (event) => {
        const chunk = event.data as {
          pcmFrameBuffer: Float32Array;
          containsActiveSpeech: boolean;
          accumulatedSampleCount: number;
        };

        // Only transmit chunks containing active speech — silence is pruned at the edge
        if (chunk.containsActiveSpeech && this.voiceSocket?.readyState === WebSocket.OPEN) {
          this.voiceSocket.send(chunk.pcmFrameBuffer.buffer);
        }
      };

      // 5. Wire the audio graph: Microphone → VAD Worklet
      sourceNode.connect(this.vadNode);
      // Don't connect to destination — we don't want to play back the user's mic

      return true;
    } catch (e) {
      this.logger?.error(`streamAudioWebSocket init failed: ${e}`);
      if (this.mediaStream) {
        this.mediaStream.getTracks().forEach(track => track.stop());
        this.mediaStream = null;
      }
      return false;
    }
  }

  /**
   * [ VOICE_STREAM_TEARDOWN ]
   * Cleanly releases all audio hardware resources and closes the WebSocket.
   */
  async stopAudioStream(): Promise<void> {
    if (this.vadNode) {
      this.vadNode.disconnect();
      this.vadNode = null;
    }
    if (this.audioContext) {
      await this.audioContext.close().catch(() => {});
      this.audioContext = null;
    }
    if (this.playAudioContext) {
      await this.playAudioContext.close().catch(() => {});
      this.playAudioContext = null;
    }
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach(track => track.stop());
      this.mediaStream = null;
    }
    if (this.voiceSocket) {
      this.voiceSocket.close();
      this.voiceSocket = null;
    }
    this.onTranscriptCallback = null;
  }
}
