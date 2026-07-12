import React, { useState } from 'react';
import { useStore } from '../store/useStore';
import { ToolManifest } from '../types';
import { X, Cpu, ShieldAlert, FileJson } from 'lucide-react';
import { ReferenceDocsWidget } from './ReferenceDocsWidget';
import { SchemaNodeBuilder, JSONSchema } from './SchemaNodeBuilder';
import { getCsrfToken } from '../csrfStore';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || '';

interface ToolBuilderWizardProps {
  onClose: () => void;
}

const ToolBuilderWizard: React.FC<ToolBuilderWizardProps> = ({ onClose }) => {
  const { tools, setTools, toolToEdit, modelFallbackMessage } = useStore();
  const [step, setStep] = useState(0);
  const [isSaving, setIsSaving] = useState(false);
  const [isIngesting, setIsIngesting] = useState(false);
  
  const [formData, setFormData] = useState<Partial<ToolManifest>>(
    toolToEdit || {
      id: '',
      name: '',
      description: '',
      enabled: true,
      capabilities: {},
      schema: { type: 'object', properties: {}, required: [] },
      permissions: []
    }
  );

  const [autoConfigUrl, setAutoConfigUrl] = useState('');
  const [autoConfigUrls, setAutoConfigUrls] = useState<string[]>(['']);
  const [autoConfigType, setAutoConfigType] = useState('openapi');
  const [deepCrawl, setDeepCrawl] = useState(false);
  const [sandboxResult, setSandboxResult] = useState<any>(null);
  const [userPrompt, setUserPrompt] = useState('');
  const [ingestMessages, setIngestMessages] = useState<string[]>([]);
  const [activeCapTab, setActiveCapTab] = useState<string>('api');
  
  // Environment variables UI state
  const [envVarKey, setEnvVarKey] = useState('');
  const [envVarValue, setEnvVarValue] = useState('');

  // OAuth2 Device Flow State
  const [oauthDeviceState, setOauthDeviceState] = useState<{
    user_code?: string;
    verification_uri?: string;
    status: 'idle' | 'pending' | 'success' | 'error';
    message?: string;
  }>({ status: 'idle' });

  const handleChange = (field: keyof ToolManifest, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleCapabilityChange = (capKey: string, field: string, value: any) => {
    setFormData(prev => {
      const caps = { ...(prev.capabilities || {}) };
      caps[capKey] = { ...(caps[capKey] || { type: capKey.toUpperCase() }), [field]: value };
      return { ...prev, capabilities: caps };
    });
  };

  const addCapability = (type: string) => {
    const key = type.toLowerCase();
    if (!formData.capabilities?.[key]) {
      handleCapabilityChange(key, 'type', type);
      setActiveCapTab(key);
    }
  };

  const removeCapability = (key: string) => {
    setFormData(prev => {
      const caps = { ...prev.capabilities };
      delete caps[key];
      const remaining = Object.keys(caps);
      if (remaining.length > 0 && activeCapTab === key) {
        setActiveCapTab(remaining[0]);
      }
      return { ...prev, capabilities: caps };
    });
  };

  const handleStoreSecret = async (secret: string): Promise<string | null> => {
    try {
      const token = localStorage.getItem('alluci_daemon_token');
      const res = await fetch(`${DAEMON_URL}/api/v1/vault/tool-secrets`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify({ secret_value: secret })
      });
      const data = await res.json();
      if (data.vault_id) return data.vault_id;
    } catch (e) {
      console.error("Failed to store secret", e);
    }
    return null;
  };

  const handleAddEnvVar = async () => {
    if (!envVarKey || !envVarValue) return;
    const vaultId = await handleStoreSecret(envVarValue);
    if (vaultId) {
      const existingEnvVars = formData.capabilities?.[activeCapTab]?.envVarsVaultId || {};
      handleCapabilityChange(activeCapTab, 'envVarsVaultId', {
        ...existingEnvVars,
        [envVarKey]: vaultId
      });
      setEnvVarKey('');
      setEnvVarValue('');
    }
  };

  const handleRemoveEnvVar = (key: string) => {
    const existingEnvVars = { ...(formData.capabilities?.[activeCapTab]?.envVarsVaultId || {}) };
    delete existingEnvVars[key];
    handleCapabilityChange(activeCapTab, 'envVarsVaultId', existingEnvVars);
  };

  // Detect URLs that won't return raw JSON (GitHub repos, docs sites, etc.)
  const isNonJsonUrl = (url: string): boolean => {
    try {
      const parsed = new URL(url);
      const host = parsed.hostname.toLowerCase();
      const path = parsed.pathname.toLowerCase();
      // GitHub repos, GitLab, Bitbucket, documentation sites
      if (['github.com', 'www.github.com', 'gitlab.com', 'bitbucket.org'].includes(host)) return true;
      // Common documentation domains
      if (host.includes('docs.') || host.includes('wiki.') || host.includes('readme.')) return true;
      // If path doesn't end with .json or .yaml, it's likely HTML
      if (!path.endsWith('.json') && !path.endsWith('.yaml') && !path.endsWith('.yml')) return true;
      return false;
    } catch (_e) { return false; }
  };

  const handleAutoConfig = async () => {
    let effectiveType = autoConfigType;
    let effectiveUrls = autoConfigUrls.map(u => u.trim()).filter(Boolean);
    let effectiveUrl = autoConfigUrl.trim();

    // Content-type guard: auto-switch to smart_ingest for non-JSON URLs
    if (effectiveType !== 'smart_ingest' && effectiveUrl && isNonJsonUrl(effectiveUrl)) {
      console.log(`[AutoConfig] Detected non-JSON URL "${effectiveUrl}", switching to Smart Ingestion`);
      // Migrate the single URL into the multi-URL smart ingest flow
      effectiveType = 'smart_ingest';
      effectiveUrls = [effectiveUrl];
      // Update UI state so the user sees the switch
      setAutoConfigType('smart_ingest');
      setAutoConfigUrls([effectiveUrl]);
    }

    const isSmart = effectiveType === 'smart_ingest';
    
    if (isSmart && effectiveUrls.length === 0) return;
    if (!isSmart && !effectiveUrl) return;
    
    setIsIngesting(true);
    setIngestMessages([]);
    try {
      const token = localStorage.getItem('alluci_daemon_token');
      const csrfToken = await getCsrfToken(DAEMON_URL, token);
      
      const payload = isSmart 
        ? { urls: effectiveUrls, type: effectiveType, user_prompt: userPrompt, deep_crawl: deepCrawl }
        : { url: effectiveUrl, type: effectiveType };

      const res = await fetch(`${DAEMON_URL}/api/v1/tools/ingest`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
          ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {})
        },
        body: JSON.stringify(payload)
      });
      
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        alert('Failed to start ingestion: ' + (errorData.detail || errorData.message || res.statusText));
        setIsIngesting(false);
        return;
      }
      
      // Detect SSE stream: either because we're in smart mode, or the backend rerouted
      const responseContentType = res.headers.get('content-type') || '';
      const isSSEStream = isSmart || responseContentType.includes('text/event-stream');
      
      if (isSSEStream && res.body) {
        const reader = res.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n\n');
          buffer = lines.pop() || '';
          for (const line of lines) {
            if (line.startsWith('data: ')) {
               try {
                 const data = JSON.parse(line.replace('data: ', ''));
                 if (data.type === 'progress') setIngestMessages(prev => [...prev, data.message]);
                 if (data.type === 'success') {
                    setFormData(prev => ({ ...prev, ...data.manifest }));
                    setStep(1);
                 }
                 if (data.type === 'error') {
                    alert('Ingestion error: ' + data.message);
                 }
               } catch(e) {}
            }
          }
        }
      } else {
        const data = await res.json();
        if (res.ok && data.manifest) {
          setFormData(prev => ({ ...prev, ...data.manifest }));
          setStep(1); // Proceed to metadata to review
        } else {
          alert("Ingestion failed: " + (data.detail || "Unknown error"));
        }
      }
    } catch (e) {
      console.error("Ingestion failed", e);
      alert("Failed to reach ingest endpoint");
    } finally {
      setIsIngesting(false);
    }
  };

  const initiateDeviceAuth = async () => {
    setOauthDeviceState({ status: 'pending', message: 'Initiating...' });
    try {
      const token = localStorage.getItem('alluci_daemon_token');
      const res = await fetch(`${DAEMON_URL}/api/v1/tools/oauth2/device-auth`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify({ target_domain: formData.capabilities?.[activeCapTab]?.baseUrl })
      });
      const data = await res.json();
      if (res.ok && data.user_code) {
        setOauthDeviceState({
          status: 'pending',
          user_code: data.user_code,
          verification_uri: data.verification_uri,
          message: 'Waiting for authorization...'
        });
        
        // Start polling simulation (in a real app, backend pushes SSE or we poll an endpoint)
        pollDeviceAuth(data.device_code);
      } else {
        setOauthDeviceState({ status: 'error', message: data.detail || 'Failed to initiate' });
      }
    } catch (e) {
      setOauthDeviceState({ status: 'error', message: 'Network error' });
    }
  };

  const pollDeviceAuth = async (deviceCode: string) => {
    // We assume backend handles the heavy polling, and we just check status periodically
    const checkInterval = setInterval(async () => {
      try {
        const token = localStorage.getItem('alluci_daemon_token');
        const res = await fetch(`${DAEMON_URL}/api/v1/tools/oauth2/status?device_code=${deviceCode}`, {
          headers: { ...(token ? { 'Authorization': `Bearer ${token}` } : {}) }
        });
        const data = await res.json();
        if (data.status === 'success') {
           clearInterval(checkInterval);
           setOauthDeviceState({ status: 'success', message: 'Authorized! Secret stored in Vault.' });
           handleCapabilityChange(activeCapTab, 'authHeadersVaultId', data.vault_id);
        } else if (data.status === 'error') {
           clearInterval(checkInterval);
           setOauthDeviceState({ status: 'error', message: data.message });
        }
      } catch (e) {}
    }, 5000);
  };

  const runSandboxTest = async () => {
    try {
      setSandboxResult({ status: 'running' });
      const token = localStorage.getItem('alluci_daemon_token');
      const res = await fetch(`${DAEMON_URL}/api/v1/tools/test_sandbox`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify({ manifest: formData, params: {} })
      });
      const data = await res.json();
      setSandboxResult(data);
    } catch (e: any) {
      setSandboxResult({ error: e.message || 'Execution failed' });
    }
  };

  const handleSave = async () => {
    if (!formData.id || !formData.name) return;
    setIsSaving(true);
    try {
      const token = localStorage.getItem('alluci_daemon_token');
      const res = await fetch(`${DAEMON_URL}/api/v1/tools/${formData.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify(formData)
      });
      
      if (res.ok) {
        if (toolToEdit) {
          setTools(prev => prev.map(t => t.id === formData.id ? formData as ToolManifest : t));
        } else {
          setTools(prev => [...prev, formData as ToolManifest]);
        }
        onClose();
      } else {
        alert("Failed to save to registry");
      }
    } catch (e) {
      console.error("Save failed", e);
    } finally {
      setIsSaving(false);
    }
  };

  const generatePreviewCommand = () => {
    const ex = formData.execution;
    if (ex?.type === 'API') {
      const authHeader = ex.authHeadersVaultId ? `\n  -H "Authorization: Bearer ********"` : '';
      return `curl -X ${ex.method || 'GET'} ${ex.baseUrl || ''}${ex.endpoint || ''} ${authHeader}`;
    } else if (ex?.type === 'CLI' || (ex?.type === 'MCP' && ex.transport === 'stdio')) {
      const envVars = Object.keys(ex.envVarsVaultId || {}).map(k => `${k}=********`).join(' ');
      return `${envVars ? envVars + ' ' : ''}${ex.command || 'executable'}`;
    }
    return 'JSON-RPC over SSE or Unsupported transport';
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-md p-4 animate-in fade-in duration-200">
      <div className="bg-glass-1 border border-glass-edge rounded-2xl w-full max-w-6xl max-h-[90vh] flex flex-col shadow-2xl relative overflow-hidden">
        
        {/* Header */}
        <div className="p-6 border-b border-glass-edge flex items-center justify-between bg-glass-2 relative z-10">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-accent/10 rounded-xl border border-accent/20">
              <Cpu className="text-accent w-6 h-6" />
            </div>
            <div>
              <h2 className="text-xl font-bold tracking-tight text-text-primary">
                {toolToEdit ? 'Edit Tool Adapter' : 'Build Native Tool'}
              </h2>
              <p className="text-xs text-text-tertiary mt-1 font-mono uppercase tracking-wider">
                Step {step + 1} of 6
              </p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-glass-3 rounded-xl transition-colors">
            <X className="w-5 h-5 text-text-tertiary" />
          </button>
        </div>

        {/* Progress Bar */}
        <div className="flex gap-1 h-1 w-full overflow-hidden bg-glass-1">
          {[0, 1, 2, 3, 4, 5].map(i => (
            <div key={i} className="flex-1 transition-all duration-500" style={{ background: i <= step ? 'var(--liquid-accent)' : 'transparent' }} />
          ))}
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar relative z-10 flex">
          {/* Main Steps */}
          <div className="flex-1 pr-6 border-r border-glass-edge">
            
            {step === 0 && (
              <div className="space-y-4">
                <h3 className="text-sm font-bold text-accent">0. Auto-Configuration</h3>
                <p className="text-xs text-text-secondary">Paste an OpenAPI spec URL or MCP tools/list SSE endpoint to auto-generate the tool configuration.</p>
                <div className="flex gap-2">
                  <select 
                    value={autoConfigType} 
                    onChange={e => setAutoConfigType(e.target.value)}
                    className="bg-glass-pressed border border-glass-edge rounded-xl p-3 text-sm text-text-primary outline-none"
                  >
                    <option value="openapi">OpenAPI/Swagger</option>
                    <option value="mcp_sse">MCP SSE</option>
                    <option value="smart_ingest">Smart Ingestion (Docs/URL)</option>
                  </select>
                  {autoConfigType === 'smart_ingest' ? (
                    <div className="flex-1 flex flex-col gap-2">
                      {autoConfigUrls.map((url, idx) => {
                        let progress = 0;
                        let activeSubpage = '';
                        if (isIngesting && url) {
                            try {
                                const domain = new URL(url).hostname;
                                const relatedMsgs = ingestMessages.filter(m => m.includes(domain));
                                if (relatedMsgs.length > 0) {
                                    const latest = relatedMsgs[relatedMsgs.length - 1];
                                    const match = latest.match(/Crawled (\d+)\/(\d+)/);
                                    if (match) {
                                        progress = (parseInt(match[1]) / parseInt(match[2])) * 100;
                                    } else {
                                        progress = 100; // Synthesis phase or fast fetch
                                    }
                                    activeSubpage = latest.split('pages: ')[1] || 'Synthesizing...';
                                } else if (ingestMessages.length > 0) {
                                    progress = 10; // Started but no specific message yet
                                }
                            } catch(e) {}
                        }

                        return (
                          <div key={idx} className="flex flex-col gap-1 w-full">
                            <div className="flex gap-2 w-full">
                              <input
                                type="text"
                                value={url}
                                onChange={e => {
                                  const newUrls = [...autoConfigUrls];
                                  newUrls[idx] = e.target.value;
                                  setAutoConfigUrls(newUrls);
                                }}
                                placeholder="https://example.com/docs"
                                className="flex-1 bg-glass-pressed border border-glass-edge rounded-xl p-3 text-sm text-text-primary focus:border-accent outline-none"
                              />
                              <button 
                                disabled={autoConfigUrls.length === 1}
                                onClick={() => {
                                  setAutoConfigUrls(autoConfigUrls.filter((_, i) => i !== idx));
                                }}
                                className="glass-btn px-3 flex items-center justify-center text-text-secondary hover:text-red-400 disabled:opacity-50"
                              >
                                <span className="text-xl font-bold leading-none">&minus;</span>
                              </button>
                            </div>
                            {isIngesting && url && progress > 0 && (
                              <div className="w-full pl-2 pr-12 mt-1">
                                <div className="flex justify-between text-[8px] text-accent font-mono mb-1">
                                    <span className="truncate max-w-[80%]">{activeSubpage || 'Processing...'}</span>
                                    <span>{Math.round(progress)}%</span>
                                </div>
                                <div className="h-1 w-full bg-glass-pressed rounded overflow-hidden">
                                    <div 
                                      className={`h-full bg-accent transition-all duration-300 ${progress === 100 ? 'animate-pulse' : ''}`}
                                      style={{ width: `${progress}%` }} 
                                    />
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })}
                      <div className="flex items-center justify-between mt-1">
                        <button 
                          onClick={() => setAutoConfigUrls([...autoConfigUrls, ''])}
                          className="glass-btn self-start px-3 py-1 text-xs flex items-center gap-1"
                        >
                          <span className="text-lg font-bold leading-none">+</span> Add Link
                        </button>
                        <label className="flex items-center gap-2 text-xs text-text-secondary cursor-pointer hover:text-text-primary transition-colors">
                          <input
                            type="checkbox"
                            checked={deepCrawl}
                            onChange={(e) => setDeepCrawl(e.target.checked)}
                            className="w-3.5 h-3.5 rounded bg-glass border-glass-edge text-accent focus:ring-accent focus:ring-offset-background"
                          />
                          Deep Crawl (Follow sub-links)
                        </label>
                      </div>
                    </div>
                  ) : (
                    <input
                      type="text"
                      value={autoConfigUrl}
                      onChange={e => setAutoConfigUrl(e.target.value)}
                      placeholder="https://api.example.com/swagger.json"
                      className="flex-1 bg-glass-pressed border border-glass-edge rounded-xl p-3 text-sm text-text-primary focus:border-accent outline-none"
                    />
                  )}
                  <button onClick={handleAutoConfig} disabled={isIngesting} className="glass-btn glass-btn--primary relative overflow-hidden group">
                        {isIngesting ? 'Processing Neural Engine...' : 'Auto-Fill Configuration'}
                        {isIngesting && <div className="absolute inset-0 bg-white/10 animate-pulse" />}
                      </button>
                </div>
                
                {autoConfigType === 'smart_ingest' && (
                  <div className="mt-2">
                    <textarea 
                      value={userPrompt}
                      onChange={e => setUserPrompt(e.target.value)}
                      placeholder="Optional: Provide context. e.g. 'I only want the sendMessage endpoint.'"
                      className="w-full h-16 bg-glass-pressed border border-glass-edge rounded-xl p-3 text-sm text-text-primary outline-none focus:border-accent"
                    />
                  </div>
                )}
                
                {modelFallbackMessage && isIngesting && autoConfigType === 'smart_ingest' && (
                  <div className="mt-2 p-2 bg-yellow-900/20 border border-yellow-700/50 rounded text-yellow-500 text-xs">
                    {modelFallbackMessage}
                  </div>
                )}
                
                {isIngesting && autoConfigType === 'smart_ingest' && ingestMessages.length > 0 && (
                  <div className="mt-2 p-3 bg-glass-pressed border border-glass-edge rounded-xl text-xs space-y-1 font-mono text-text-secondary h-32 overflow-y-auto custom-scrollbar flex flex-col">
                    {ingestMessages.map((msg, idx) => (
                      <div key={idx} className={idx === ingestMessages.length - 1 ? "text-accent" : "opacity-70"}>
                        &gt; {msg}
                      </div>
                    ))}
                  </div>
                )}

                <div className="mt-4">
                  <button onClick={() => setStep(1)} className="text-xs text-accent underline">Skip auto-config and build manually</button>
                </div>
              </div>
            )}

            {step === 1 && (
              <div className="space-y-4">
                <h3 className="text-sm font-bold text-accent">1. Extrinsic Metadata</h3>
                <div className="space-y-2">
                  <label className="text-[10px] uppercase font-mono tracking-widest text-text-secondary">Identifier</label>
                  <input
                    type="text"
                    value={formData.id}
                    onChange={e => handleChange('id', e.target.value)}
                    placeholder="e.g., bridge_gmail"
                    className="w-full bg-glass-pressed border border-glass-edge rounded-xl p-3 text-sm text-text-primary"
                    disabled={!!toolToEdit}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] uppercase font-mono tracking-widest text-text-secondary">Display Name</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={e => handleChange('name', e.target.value)}
                    className="w-full bg-glass-pressed border border-glass-edge rounded-xl p-3 text-sm text-text-primary"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] uppercase font-mono tracking-widest text-text-secondary">Category</label>
                  <select
                    value={formData.category}
                    onChange={e => {
                      handleChange('category', e.target.value);
                      handleCapabilityChange(activeCapTab, 'type', e.target.value);
                    }}
                    className="w-full bg-glass-pressed border border-glass-edge rounded-xl p-3 text-sm text-text-primary"
                  >
                    <option value="API">API</option>
                    <option value="MCP">MCP Server</option>
                    <option value="CLI">CLI Utility</option>
                    <option value="RPC">RPC</option>
                    <option value="TOOL">Standard Tool</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] uppercase font-mono tracking-widest text-text-secondary">Description</label>
                  <textarea
                    value={formData.description}
                    onChange={e => handleChange('description', e.target.value)}
                    className="w-full bg-glass-pressed border border-glass-edge rounded-xl p-3 text-sm text-text-primary h-24"
                  />
                </div>
              </div>
            )}

            {step === 2 && (
              <div className="space-y-6">
                <h3 className="text-sm font-bold text-accent flex items-center justify-between">
                  <span>2. Capabilities (Tool Engine)</span>
                  <div className="flex gap-2">
                    <button onClick={() => addCapability('API')} className="glass-btn px-2 text-xs">+ API</button>
                    <button onClick={() => addCapability('CLI')} className="glass-btn px-2 text-xs">+ CLI</button>
                    <button onClick={() => addCapability('MCP')} className="glass-btn px-2 text-xs">+ MCP</button>
                  </div>
                </h3>
                
                {!formData.capabilities || Object.keys(formData.capabilities).length === 0 ? (
                  <div className="p-8 text-center border border-dashed border-glass-edge rounded-xl text-text-tertiary">
                    No capabilities configured. Auto-Fill to extract them or add manually above.
                  </div>
                ) : (
                  <div>
                    {/* Tabs */}
                    <div className="flex gap-2 mb-4 overflow-x-auto custom-scrollbar pb-2">
                      {Object.keys(formData.capabilities).map(cap => (
                        <div key={cap} className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border cursor-pointer ${activeCapTab === cap ? 'bg-glass-3 border-accent text-accent' : 'bg-glass border-glass-edge text-text-secondary hover:text-text-primary'}`} onClick={() => setActiveCapTab(cap)}>
                          <span className="text-xs font-bold uppercase">{cap}</span>
                          <button onClick={(e) => { e.stopPropagation(); removeCapability(cap); }} className="hover:text-red-400 opacity-50 hover:opacity-100">
                            <X className="w-3 h-3" />
                          </button>
                        </div>
                      ))}
                    </div>
                    
                    {/* Active Capability Panel */}
                    {activeCapTab && formData.capabilities[activeCapTab] && (
                      <div className="p-4 bg-glass border border-glass-edge rounded-xl space-y-4">
                        {(formData.capabilities[activeCapTab].type === 'API' || formData.capabilities[activeCapTab].type === 'RPC') && (
                          <>
                            <div className="flex gap-2">
                              <div className="w-1/3 space-y-2">
                                <label className="text-[10px] uppercase font-mono tracking-widest text-text-secondary">Method</label>
                                <select
                                  value={formData.capabilities[activeCapTab].method || 'GET'}
                                  onChange={e => handleCapabilityChange(activeCapTab, 'method', e.target.value)}
                                  className="w-full bg-glass-pressed border border-glass-edge rounded-xl p-3 text-sm text-text-primary"
                                >
                                  <option value="GET">GET</option>
                                  <option value="POST">POST</option>
                                  <option value="PUT">PUT</option>
                                  <option value="DELETE">DELETE</option>
                                </select>
                              </div>
                              <div className="flex-1 space-y-2">
                                <label className="text-[10px] uppercase font-mono tracking-widest text-text-secondary">Base URL</label>
                                <input
                                  type="text"
                                  value={formData.capabilities[activeCapTab].baseUrl || ''}
                                  onChange={e => handleCapabilityChange(activeCapTab, 'baseUrl', e.target.value)}
                                  placeholder="https://api.example.com/v1"
                                  className="w-full bg-glass-pressed border border-glass-edge rounded-xl p-3 text-sm text-text-primary"
                                />
                              </div>
                            </div>
                            <div className="space-y-2">
                              <label className="text-[10px] uppercase font-mono tracking-widest text-text-secondary">Endpoint Path</label>
                              <input
                                type="text"
                                value={formData.capabilities[activeCapTab].endpoint || ''}
                                onChange={e => handleCapabilityChange(activeCapTab, 'endpoint', e.target.value)}
                                placeholder="/users"
                                className="w-full bg-glass-pressed border border-glass-edge rounded-xl p-3 text-sm text-text-primary font-mono"
                              />
                            </div>
                            
                            <div className="space-y-2 mt-4">
                              <label className="text-[10px] uppercase font-mono tracking-widest text-text-secondary">Authorization Type</label>
                              <select
                                value={formData.capabilities[activeCapTab].authType || 'apikey'}
                                onChange={e => handleCapabilityChange(activeCapTab, 'authType', e.target.value)}
                                className="w-full bg-glass-pressed border border-glass-edge rounded-xl p-3 text-sm text-text-primary"
                              >
                                <option value="apikey">API Key / Bearer Token</option>
                                <option value="oauth2">OAuth2 (Device Grant)</option>
                              </select>
                            </div>
                            
                            {formData.capabilities[activeCapTab].authType === 'oauth2' ? (
                              <div className="p-4 bg-glass-pressed border border-glass-edge rounded-xl space-y-4">
                                <p className="text-xs text-text-secondary">OAuth2 Configuration</p>
                              </div>
                            ) : (
                              <div className="space-y-2">
                                <label className="text-[10px] uppercase font-mono tracking-widest text-text-secondary">Auth Header Secret (Vault Routed)</label>
                                <input
                                  type="password"
                                  placeholder={formData.capabilities[activeCapTab].authHeadersVaultId ? "•••••••••••••••• (Secured in Vault)" : "Bearer token..."}
                                  onBlur={async (e) => {
                                    if (e.target.value && !e.target.value.includes('••••')) {
                                      const vaultId = await handleStoreSecret(e.target.value);
                                      if (vaultId) {
                                          handleCapabilityChange(activeCapTab, 'authHeadersVaultId', vaultId);
                                          e.target.value = "•••••••••••••••• (Secured in Vault)";
                                      }
                                    }
                                  }}
                                  className="w-full bg-glass-pressed border border-glass-edge rounded-xl p-3 text-sm text-text-primary"
                                />
                              </div>
                            )}
                          </>
                        )}
                        
                        {(formData.capabilities[activeCapTab].type === 'MCP' || formData.capabilities[activeCapTab].type === 'CLI') && (
                          <>
                            {formData.capabilities[activeCapTab].type === 'MCP' && (
                              <div className="space-y-2">
                                <label className="text-[10px] uppercase font-mono tracking-widest text-text-secondary">Transport</label>
                                <select
                                  value={formData.capabilities[activeCapTab].transport || 'stdio'}
                                  onChange={e => handleCapabilityChange(activeCapTab, 'transport', e.target.value)}
                                  className="w-full bg-glass-pressed border border-glass-edge rounded-xl p-3 text-sm text-text-primary"
                                >
                                  <option value="stdio">stdio (Local Command)</option>
                                  <option value="sse">SSE (Network)</option>
                                </select>
                              </div>
                            )}

                            {(formData.capabilities[activeCapTab].type === 'CLI' || formData.capabilities[activeCapTab].transport === 'stdio') ? (
                                <div className="space-y-2">
                                  <label className="text-[10px] uppercase font-mono tracking-widest text-text-secondary">Execution Command</label>
                                  <input
                                      type="text"
                                      value={formData.capabilities[activeCapTab].command || ''}
                                      onChange={e => handleCapabilityChange(activeCapTab, 'command', e.target.value)}
                                      className="w-full bg-glass-pressed border border-glass-edge rounded-xl p-3 text-sm text-text-primary font-mono"
                                  />
                                </div>
                            ) : (
                                <div className="space-y-2">
                                  <label className="text-[10px] uppercase font-mono tracking-widest text-text-secondary">SSE URL</label>
                                  <input
                                      type="text"
                                      value={formData.capabilities[activeCapTab].url || ''}
                                      onChange={e => handleCapabilityChange(activeCapTab, 'url', e.target.value)}
                                      className="w-full bg-glass-pressed border border-glass-edge rounded-xl p-3 text-sm text-text-primary"
                                  />
                                </div>
                            )}
                          </>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {step === 3 && (
              <div className="space-y-4">
                <h3 className="text-sm font-bold text-accent">3. Schema Builder</h3>
                <p className="text-xs text-text-secondary">Define parameter constraints. Supports nested objects.</p>
                <div className="bg-black/20 border border-glass-edge rounded-xl p-4 overflow-x-auto">
                  <SchemaNodeBuilder 
                    schema={(formData.schema as JSONSchema) || { type: 'object', properties: {}, required: [] }} 
                    onChange={(s) => handleChange('schema', s)} 
                  />
                </div>
              </div>
            )}

            {step === 4 && (
              <div className="space-y-4">
                <h3 className="text-sm font-bold text-accent">4. Knowledge Grounding</h3>
                <ReferenceDocsWidget
                    label="Reference Documentation (.md or URLs)"
                    items={formData.reference_docs || []}
                    onChange={items => handleChange('reference_docs', items)}
                    placeholder="Add OpenAPI specs, MCP guides, or local file paths..."
                />
              </div>
            )}

            {step === 5 && (
              <div className="space-y-4">
                <h3 className="text-sm font-bold text-accent">5. Testing Sandbox & PCL</h3>
                <p className="text-xs text-text-secondary">Execute a mock request in the local sandbox. The Guardian Scanner will verify the payload first to prevent Topological Ruptures.</p>
                
                <div className="bg-glass-pressed border border-glass-edge rounded p-3 mb-4">
                  <h4 className="text-[10px] uppercase tracking-widest text-text-tertiary mb-2">Compiled Execution Context</h4>
                  <pre className="text-xs text-blue-200 font-mono whitespace-pre-wrap">
                    {generatePreviewCommand()}
                  </pre>
                </div>

                <button onClick={runSandboxTest} className="glass-btn glass-btn--primary">
                  <ShieldAlert className="w-4 h-4 mr-2" />
                  Run Sandbox Execution
                </button>

                {sandboxResult && (
                  <div className="mt-4 p-4 bg-black/40 border border-glass-edge rounded-xl">
                    <pre className="text-[10px] font-mono text-text-primary overflow-x-auto">
                        {JSON.stringify(sandboxResult, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            )}

            <div className="flex justify-between mt-8 pt-4 border-t border-glass-edge">
              <button disabled={step === 0} onClick={() => setStep(step - 1)} className="px-4 py-2 text-sm text-text-secondary hover:text-text-primary disabled:opacity-30">Back</button>
              {step < 5 ? (
                <button onClick={() => setStep(step + 1)} className="glass-btn glass-btn--primary px-6">Next Step</button>
              ) : (
                <button onClick={handleSave} disabled={!formData.id || !formData.name || isSaving} className="glass-btn glass-btn--primary px-6">
                  {isSaving ? 'Saving...' : 'Save Tool to Registry'}
                </button>
              )}
            </div>

          </div>

          {/* Right Sidebar - JSON Preview */}
          <div className="w-2/5 pl-6 hidden md:block">
            <h4 className="text-[10px] uppercase tracking-widest text-text-tertiary mb-4 flex items-center gap-2">
                <FileJson className="w-3 h-3" /> Live Manifest Preview
            </h4>
            <pre className="text-[8px] font-mono overflow-auto h-full opacity-70 text-text-primary">
              {JSON.stringify(formData, null, 2)}
            </pre>
          </div>
        </div>

      </div>
    </div>
  );
};

export default ToolBuilderWizard;