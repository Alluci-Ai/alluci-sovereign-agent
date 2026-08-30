// geminiService.ts — RE-APPLIED FIX

// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { GoogleGenAI, LiveServerMessage, Modality, Blob, GenerateContentResponse, FunctionDeclaration, Type } from '@google/genai';
import { AuditLedger, generateSystemPrompt } from './alluciCore';
import { PersonalityTraits, Connection, SkillManifest, SoulManifest } from './types';
import { AutonomyLevel, AceStateVector } from './kernel/types';
import { getCsrfToken } from './csrfStore';
import { submitObjective } from './lib/objectiveService';
import { useStore } from './store/useStore';

// Exported GroundingSource for UI reference list
export interface GroundingSource {
  uri: string;
  title: string;
}

export interface GeminiCallbacks {
  onAudioOutput: (base64Audio: string) => void;
  onTranscription: (text: string, isUser: boolean) => void;
  onInterrupted?: () => void;
  onOpen?: () => void;
  onClose?: () => void;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  onError?: (error: any) => void;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  onToolCall?: (fc: any) => void;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
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
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private sessionPromise: Promise<any> | null = null;
  private inputAudioContext: AudioContext | null = null;
  private audioWorkletNode: AudioWorkletNode | null = null;
  public audit: AuditLedger = new AuditLedger();
  private currentPersonality: SoulManifest | PersonalityTraits = { satireLevel: 0.5, analyticalDepth: 0.8, protectiveBias: 0.9, verbosity: 0.4 };
  private currentConnections: Connection[] = [];
  private currentSkills: SkillManifest[] = [];
  private DAEMON_URL = import.meta.env.VITE_DAEMON_URL || '';

  setPersonality(traits: SoulManifest | PersonalityTraits) { this.currentPersonality = traits; }
  setConnections(connections: Connection[]) { this.currentConnections = connections; }
  setSkills(skills: SkillManifest[]) { this.currentSkills = skills; }

  private getAuthToken(): string | null {
    try {
      return localStorage.getItem('alluci_access_token');
    } catch {
      return null;
    }
  }

  private getApiKey(): string | null {
    return null; 
  }

  sendVideoFrame(base64Data: string) {
    this.sessionPromise?.then((session) => {
      session.sendRealtimeInput({
        media: { data: base64Data, mimeType: 'image/jpeg' }
      });
    });
  }

  sendRealtimeInput(data: Float32Array) {
    this.sessionPromise?.then((session) => {
      session.sendRealtimeInput({
        media: this.createBlob(data)
      });
    });
  }

  private async checkSession(): Promise<boolean> {
    try {
      const res = await fetch(`${this.DAEMON_URL}/api/v1/health`, { credentials: 'include' });
      return res.ok;
    } catch {
      return false;
    }
  }

  async connect(callbacks: GeminiCallbacks) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    this.inputAudioContext = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 });
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

    const tokenAvailable = await this.checkSession();
    if (!tokenAvailable) {
      callbacks.onError(new Error('Unauthorized. Please authenticate via the Sovereign Wizard.'));
      return null;
    }

    const apiKey = "PROXIED"; 

    const ai = new GoogleGenAI({ apiKey });
    this.sessionPromise = ai.live.connect({
      model: 'gemini-2.5-pro-preview-05-06',
      callbacks: {
        onopen: async () => {
          callbacks.onOpen?.();
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
          if (message.serverContent?.interrupted) callbacks.onInterrupted?.();

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
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        onerror: (e: any) => callbacks.onError?.(e),
        onclose: () => callbacks.onClose?.(),
      },
      config: {
        responseModalities: [Modality.AUDIO],
        speechConfig: { voiceConfig: { prebuiltVoiceConfig: { voiceName: 'Kore' } } },
        systemInstruction: generateSystemPrompt(this.currentPersonality, this.currentConnections, this.currentSkills),
        tools: [{ functionDeclarations: sovereignTools }],
        inputAudioTranscription: {},
        outputAudioTranscription: {},
      },
    });

    return this.sessionPromise;
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private validateToolArgs(name: string, args: any): any {
    if (typeof args !== 'object' || args === null) return {};
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const sanitized: any = {};
    for (const [key, value] of Object.entries(args)) {
      if (typeof value === 'string') {
        sanitized[key] = value.replace(/[<>]/g, '').slice(0, 2000);
      } else if (typeof value === 'number' || typeof value === 'boolean') {
        sanitized[key] = value;
      }
    }
    return sanitized;
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private async callBackendTool(name: string, args: any): Promise<string> {
    const validatedArgs = this.validateToolArgs(name, args);
    this.audit.addEntry("DAEMON_GATEWAY_REQUEST", { tool: name, args: validatedArgs });
    try {
      const autonomyLevel = (validatedArgs.autonomy_level || 'SEMI_AUTONOMOUS') as AutonomyLevel;
      const objective = validatedArgs.objective || JSON.stringify(validatedArgs);

      const state = useStore.getState();
      const token = state.accessToken || this.getAuthToken();
      
      const aceState: AceStateVector = {
        physicalEnergy: state.biometrics.physical,
        emotionalValence: state.biometrics.emotional,
        cognitiveLoad: state.biometrics.cognitive,
      };

      if (!token) return "[ ERROR ]: UNAUTHORIZED. Please authenticate via the API Manifold.";

      const result = await submitObjective(
        objective,
        autonomyLevel,
        [], // vaultScope
        [], // capabilityScope
        aceState,
        token
      );

      return JSON.stringify(result.result);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (e: any) {
      return `[ ERROR ]: ${e.message || "Daemon Connection Failed."}`;
    }
  }

  async processMultimodal(
    text: string, 
    files: FilePart[], 
    inferenceMode: string = 'HYBRID', 
    onToken?: (token: string) => void
  ): Promise<string> {
    const state = useStore.getState();
    const token = state.accessToken || this.getAuthToken();
    
    if (!token) {
      return "[ ERROR ]: Authentication required. Please log in via the Sovereign Identity portal.";
    }
 
    const executeRequest = async (forceCsrf = false, isStream = false) => {
      const csrfToken = await getCsrfToken(this.DAEMON_URL, token, forceCsrf);
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (csrfToken) headers['X-CSRF-Token'] = csrfToken;
      if (token) headers['Authorization'] = `Bearer ${token}`;
 
      const endpoint = isStream ? '/api/v1/gemini/proxy/stream' : '/api/v1/gemini/proxy';
      return await fetch(`${this.DAEMON_URL}${endpoint}`, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify({ 
          prompt: text, 
          files: files,
          complexity: 'MEDIUM', 
          inference_mode: inferenceMode,
          session_id: state.activeSessionKey
        }),
        credentials: 'include'
      });
    };
 
    let fullText = '';
    try {
      const isStream = typeof onToken === 'function';
      let response = await executeRequest(false, isStream);
      
      // If 403 (CSRF Invalid), try refreshing once
      if (response.status === 403) {
        console.warn("[ GEMINI_PROXY ]: CSRF Invalid, retrying with forced refresh...");
        response = await executeRequest(true, isStream);
      }
 
      if (response.ok) {
        if (isStream) {
          const reader = response.body?.getReader();
          const decoder = new TextDecoder();
          if (reader) {
            let buffer = '';
            try {
              // eslint-disable-next-line no-constant-condition
              while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                // Save the last partial line back to the buffer
                buffer = lines.pop() || '';
                for (const line of lines) {
                  // Ignore SSE keep-alive comments (e.g. ": ping")
                  if (line.startsWith(':')) continue;
                  if (line.startsWith('data: ')) {
                    const dataStr = line.slice(6);
                    try {
                      const parsed = JSON.parse(dataStr);
                      const tokenText = parsed.text || '';
                      fullText += tokenText;
                      if (onToken) onToken(tokenText);
                    } catch (err) {
                      console.error("Failed to parse SSE JSON chunk:", err, dataStr);
                    }
                  }
                }
              }
              // Process any remaining bytes in buffer
              if (buffer.startsWith('data: ')) {
                const dataStr = buffer.slice(6);
                try {
                  const parsed = JSON.parse(dataStr);
                  const tokenText = parsed.text || '';
                  fullText += tokenText;
                  if (onToken) onToken(tokenText);
                } catch (err) {
                  console.error("Failed to parse SSE JSON chunk:", err, dataStr);
                }
              }
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            } catch (streamErr: any) {
              console.warn("[ GEMINI_PROXY ]: Stream interrupted mid-read:", streamErr);
              if (fullText.trim().length > 0) {
                return fullText;
              }
              throw streamErr;
            }
          }
          return fullText;
        } else {
          const data = await response.json();
          return data.result || "[ SIGNAL_LOST ]";
        }
      } else {
        const errData = await response.json().catch(() => ({ detail: response.statusText }));
        return `[ ERROR ]: Backend failure (${response.status}): ${errData.detail || "Unknown error"}`;
      }
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (e: any) {
      if (fullText.trim().length > 0) {
        return fullText;
      }
      return `[ ERROR ]: Daemon connection failed: ${e.message}`;
    }
  }

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  async speak(text: string, onAudio: (base64: string) => void) {
    // Speak logic...
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

export function decode(base64: string): Uint8Array {
  const binaryString = atob(base64);
  const len = binaryString.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) bytes[i] = binaryString.charCodeAt(i);
  return bytes;
}

export async function decodeAudioData(data: Uint8Array, ctx: AudioContext, sampleRate: number, numChannels: number): Promise<AudioBuffer> {
  const dataInt16 = new Int16Array(data.buffer);
  const frameCount = dataInt16.length / numChannels;
  const buffer = ctx.createBuffer(numChannels, frameCount, sampleRate);
  for (let channel = 0; channel < numChannels; channel++) {
    const channelData = buffer.getChannelData(channel);
    for (let i = 0; i < frameCount; i++) channelData[i] = dataInt16[i * numChannels + channel] / 32768.0;
  }
  return buffer;
}
