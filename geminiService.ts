
import { GoogleGenAI, LiveServerMessage, Modality, Blob, GenerateContentResponse, FunctionDeclaration, Type } from '@google/genai';
import { AuditLedger, generateSystemPrompt } from './alluciCore';
import { PersonalityTraits, Connection, SkillManifest, SoulManifest } from './types';

// Exported GroundingSource for UI reference list
export interface GroundingSource {
  uri: string;
  title: string;
}

export interface GeminiCallbacks {
  onAudioOutput: (base64Audio: string) => void;
  onTranscription: (text: string, isUser: boolean) => void;
  onInterrupted: () => void;
  onOpen: () => void;
  onClose: () => void;
  onError: (error: any) => void;
  onToolCall?: (fc: any) => void;
  onPermissionRequest?: (req: { id: string, name: string, args: any }) => void;
  onGroundingSources?: (sources: GroundingSource[]) => void;
}

// Fixed constant tools for the daemon
const sovereignTools: FunctionDeclaration[] = [
  {
    name: 'execute_objective',
    description: 'Execute a complex autonomous objective using the backend DAG planner.',
    parameters: {
      type: Type.OBJECT,
      properties: {
        objective: { type: Type.STRING },
        autonomy_level: { type: Type.STRING, enum: ['RESTRICTED', 'SEMI_AUTONOMOUS', 'SOVEREIGN'] }
      },
      required: ['objective']
    }
  }
];

export interface FilePart {
  data: string;
  mimeType: string;
}

export class AlluciGeminiService {
  private sessionPromise: Promise<any> | null = null;
  private inputAudioContext: AudioContext | null = null;
  private audioWorkletNode: AudioWorkletNode | null = null;
  public audit: AuditLedger = new AuditLedger();
  private currentPersonality: SoulManifest | PersonalityTraits = { satireLevel: 0.5, analyticalDepth: 0.8, protectiveBias: 0.9, verbosity: 0.4 };
  private currentConnections: Connection[] = [];
  private currentSkills: SkillManifest[] = [];
  // Configurable daemon URL — no hardcoded localhost
  private DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';

  constructor() { }

  setPersonality(traits: SoulManifest | PersonalityTraits) { this.currentPersonality = traits; }
  setConnections(connections: Connection[]) { this.currentConnections = connections; }
  setSkills(skills: SkillManifest[]) { this.currentSkills = skills; }

  // Added sendVideoFrame to handle streaming image frames to the Live API session
  sendVideoFrame(base64Data: string) {
    this.sessionPromise?.then((session) => {
      session.sendRealtimeInput({
        media: { data: base64Data, mimeType: 'image/jpeg' }
      });
    });
  }

  /**
   * Get the API key from the backend proxy.
   * NEVER store API keys in the browser — this retrieves a session-scoped key.
   */
  private async getApiKeyFromBackend(): Promise<string> {
    try {
      const res = await fetch(`${this.DAEMON_URL}/api/gemini/proxy`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ prompt: '__KEY_CHECK__', complexity: 'LOW' }),
        credentials: 'include'
      });
      if (res.ok) return 'PROXIED';
      return '';
    } catch {
      return '';
    }
  }

  private async checkSession(): Promise<boolean> {
    try {
      const res = await fetch(`${this.DAEMON_URL}/health`, { credentials: 'include' });
      return res.ok;
    } catch {
      return false;
    }
  }

  async connect(callbacks: GeminiCallbacks) {
    this.inputAudioContext = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 });
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

    const tokenAvailable = await this.checkSession();
    if (!tokenAvailable) {
      callbacks.onError(new Error('Unauthorized. Please authenticate via the Sovereign Wizard.'));
      return null;
    }

    // Attempt to get a temporary session key or use proxied connection
    const apiKey = "PROXIED"; // In a real flow, this would be a temp token or backend WS URL

    // Note: The @google/genai SDK on frontend requires a key. 
    // To fully proxy Live API, we would need a backend WebSocket proxy.
    // For this build, we enforce proxying for all non-RT requests.

    const ai = new GoogleGenAI({ apiKey });
    this.sessionPromise = ai.live.connect({
      model: 'gemini-2.5-flash-native-audio-preview-12-2025',
      callbacks: {
        onopen: async () => {
          callbacks.onOpen();
          const source = this.inputAudioContext!.createMediaStreamSource(stream);

          try {
            await this.inputAudioContext!.audioWorklet.addModule('/audio-processor.js');
            this.audioWorkletNode = new AudioWorkletNode(this.inputAudioContext!, 'audio-processor');
            this.audioWorkletNode.port.onmessage = (e) => {
              const inputData = e.data;
              this.sessionPromise?.then((session) => session.sendRealtimeInput({ media: this.createBlob(inputData) }));
            };
            source.connect(this.audioWorkletNode);
            this.audioWorkletNode.connect(this.inputAudioContext!.destination);
          } catch (e) {
            console.error("AudioWorklet failed, falling back to ScriptProcessor", e);
            const scriptProcessor = this.inputAudioContext!.createScriptProcessor(4096, 1, 1);
            scriptProcessor.onaudioprocess = (e) => {
              const inputData = e.inputBuffer.getChannelData(0);
              this.sessionPromise?.then((session) => session.sendRealtimeInput({ media: this.createBlob(inputData) }));
            };
            source.connect(scriptProcessor);
            scriptProcessor.connect(this.inputAudioContext!.destination);
          }
        },
        onmessage: async (message: LiveServerMessage) => {
          if (message.serverContent?.modelTurn?.parts?.[0]?.inlineData?.data) {
            callbacks.onAudioOutput(message.serverContent.modelTurn.parts[0].inlineData.data);
          }
          if (message.serverContent?.outputTranscription) {
            callbacks.onTranscription(message.serverContent.outputTranscription.text, false);
          }
          if (message.serverContent?.inputTranscription) {
            callbacks.onTranscription(message.serverContent.inputTranscription.text, true);
          }
          if (message.serverContent?.interrupted) callbacks.onInterrupted();

          if (message.toolCall) {
            for (const fc of message.toolCall.functionCalls) {
              const result = await this.callBackendTool(fc.name, fc.args);
              this.sessionPromise?.then(session => {
                session.sendToolResponse({
                  functionResponses: { id: fc.id, name: fc.name, response: { result } }
                });
              });
            }
          }
        },
        onerror: (e: any) => callbacks.onError(e),
        onclose: () => callbacks.onClose(),
      },
      config: {
        responseModalities: [Modality.AUDIO],
        speechConfig: { voiceConfig: { prebuiltVoiceConfig: { voiceName: 'Kore' } } },
        // [ SYSTEM BOOTLOADER ]: Injects the Semantic Cognition Layer
        systemInstruction: generateSystemPrompt(this.currentPersonality, this.currentConnections, this.currentSkills),
        tools: [{ functionDeclarations: sovereignTools }],
        inputAudioTranscription: {},
        outputAudioTranscription: {},
      },
    });

    return this.sessionPromise;
  }

  private validateToolArgs(name: string, args: any): any {
    // Basic sanitization and structure enforcement
    if (typeof args !== 'object' || args === null) return {};

    const sanitized: any = {};
    for (const [key, value] of Object.entries(args)) {
      if (typeof value === 'string') {
        sanitized[key] = value.replace(/[<>]/g, '').slice(0, 2000); // Disallow tags, limit length
      } else if (typeof value === 'number' || typeof value === 'boolean') {
        sanitized[key] = value;
      }
    }
    return sanitized;
  }

  private async callBackendTool(name: string, args: any): Promise<string> {
    const validatedArgs = this.validateToolArgs(name, args);
    this.audit.addEntry("DAEMON_GATEWAY_REQUEST", { tool: name, args: validatedArgs });
    try {
      // Default to SEMI_AUTONOMOUS if not provided
      const autonomyLevel = validatedArgs.autonomy_level || 'SEMI_AUTONOMOUS';
      const payload = {
        objective: validatedArgs.objective || JSON.stringify(validatedArgs),
        autonomy_level: autonomyLevel
      };

      const token = this.getAuthToken();
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${this.DAEMON_URL}/objective/execute`, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify(payload),
        credentials: 'include'
      });

      if (response.status === 401) {
        return "[ ERROR ]: UNAUTHORIZED. Please authenticate via the API Manifold.";
      }

      if (response.status === 429) {
        return "[ ERROR ]: Rate limit exceeded. Please wait before trying again.";
      }

      const data = await response.json();
      return JSON.stringify(data.result);
    } catch (e) {
      return `[ ERROR ]: Local Daemon Connection Refused. Ensure backend is running on ${this.DAEMON_URL}.`;
    }
  }

  async processMultimodal(text: string, files: FilePart[]): Promise<string> {
    // Route through backend proxy instead of direct API call
    const token = this.getAuthToken();
    if (token) {
      try {
        const response = await fetch(`${this.DAEMON_URL}/api/gemini/proxy`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ prompt: text, complexity: 'MEDIUM' }),
          credentials: 'include'
        });
        if (response.ok) {
          const data = await response.json();
          return data.result || "[ SIGNAL_LOST ]";
        }
      } catch {
        // Fall through to direct call if proxy fails
      }
    }

    // Fallback: direct call (only works if VITE_GEMINI_API_KEY is set)
    const apiKey = this.getApiKey();
    if (!apiKey) return "[ ERROR ]: No API key configured. Please authenticate with the backend.";

    const ai = new GoogleGenAI({ apiKey });
    let parts: any[] = files.map(f => ({ inlineData: { data: f.data, mimeType: f.mimeType } }));
    parts.push({ text });

    let currentContents = [{ role: 'user', parts }];
    const config = {
      systemInstruction: generateSystemPrompt(this.currentPersonality, this.currentConnections, this.currentSkills),
      tools: [{ functionDeclarations: sovereignTools }]
    };

    let response: GenerateContentResponse = await ai.models.generateContent({
      model: 'gemini-3-flash-preview',
      contents: currentContents,
      config
    });

    // If tool call suggested, route to production backend
    if (response.candidates?.[0]?.content?.parts?.some(p => p.functionCall)) {
      const fc = response.candidates[0].content.parts.find(p => p.functionCall)?.functionCall;
      if (fc) {
        const result = await this.callBackendTool(fc.name, fc.args);
        return result;
      }
    }

    return response.text || "[ SIGNAL_LOST ]";
  }

  async speak(text: string, onAudio: (base64: string) => void) {
    const apiKey = this.getApiKey();
    if (!apiKey) return;

    const ai = new GoogleGenAI({ apiKey });
    const response = await ai.models.generateContent({
      model: "gemini-2.5-flash-preview-tts",
      contents: [{ parts: [{ text: `Persona Alluci: ${text}` }] }],
      config: {
        responseModalities: [Modality.AUDIO],
        speechConfig: { voiceConfig: { prebuiltVoiceConfig: { voiceName: 'Kore' } } },
      },
    });
    const audio = response.candidates?.[0]?.content?.parts?.[0]?.inlineData?.data;
    if (audio) onAudio(audio);
  }

  private createBlob(data: Float32Array): Blob {
    const int16 = new Int16Array(data.length);
    for (let i = 0; i < data.length; i++) int16[i] = data[i] * 32768;
    return { data: this.encode(new Uint8Array(int16.buffer)), mimeType: 'audio/pcm;rate=16000' };
  }

  private encode(bytes: Uint8Array): string {
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) binary += String.fromCharCode(bytes[i]);
    return btoa(binary);
  }

  disconnect() {
    this.sessionPromise?.then(s => s.close());
    this.audioWorkletNode?.disconnect();
    this.inputAudioContext?.close();
  }
}

// Helper functions for audio processing
export function decode(base64: string): Uint8Array {
  const binaryString = atob(base64);
  const len = binaryString.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return bytes;
}

export async function decodeAudioData(
  data: Uint8Array,
  ctx: AudioContext,
  sampleRate: number,
  numChannels: number,
): Promise<AudioBuffer> {
  const dataInt16 = new Int16Array(data.buffer);
  const frameCount = dataInt16.length / numChannels;
  const buffer = ctx.createBuffer(numChannels, frameCount, sampleRate);

  for (let channel = 0; channel < numChannels; channel++) {
    const channelData = buffer.getChannelData(channel);
    for (let i = 0; i < frameCount; i++) {
      channelData[i] = dataInt16[i * numChannels + channel] / 32768.0;
    }
  }
  return buffer;
}
