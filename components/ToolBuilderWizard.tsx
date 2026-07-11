import React, { useState, useEffect } from 'react';
import { useStore } from '../store/useStore';
import { ToolManifest } from '../types';
import { Terminal, Save, X, Cpu, ShieldAlert, Link, FileJson, Key, CheckCircle, Trash2 } from 'lucide-react';
import { ReferenceDocsWidget } from './ReferenceDocsWidget';
import { SchemaNodeBuilder, JSONSchema } from './SchemaNodeBuilder';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || '';

interface ToolBuilderWizardProps {
  onClose: () => void;
}

const ToolBuilderWizard: React.FC<ToolBuilderWizardProps> = ({ onClose }) => {
  const { tools, setTools, toolToEdit } = useStore();
  const [step, setStep] = useState(0);
  const [isSaving, setIsSaving] = useState(false);
  const [isIngesting, setIsIngesting] = useState(false);
  
  const [formData, setFormData] = useState<Partial<ToolManifest>>(
    toolToEdit || {
      id: '',
      name: '',
      category: 'TOOL',
      description: '',
      enabled: true,
      execution: { type: 'API', envVarsVaultId: {} },
      schema: { type: 'object', properties: {}, required: [] },
      permissions: []
    }
  );

  const [autoConfigUrl, setAutoConfigUrl] = useState('');
  const [autoConfigType, setAutoConfigType] = useState('openapi');
  const [sandboxResult, setSandboxResult] = useState<any>(null);
  
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

  const handleExecutionChange = (field: string, value: any) => {
    setFormData(prev => ({
      ...prev,
      execution: { ...(prev.execution || { type: 'API' }), [field]: value }
    }));
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
      const existingEnvVars = formData.execution?.envVarsVaultId || {};
      handleExecutionChange('envVarsVaultId', {
        ...existingEnvVars,
        [envVarKey]: vaultId
      });
      setEnvVarKey('');
      setEnvVarValue('');
    }
  };

  const handleRemoveEnvVar = (key: string) => {
    const existingEnvVars = { ...(formData.execution?.envVarsVaultId || {}) };
    delete existingEnvVars[key];
    handleExecutionChange('envVarsVaultId', existingEnvVars);
  };

  const handleAutoConfig = async () => {
    if (!autoConfigUrl) return;
    setIsIngesting(true);
    try {
      const token = localStorage.getItem('alluci_daemon_token');
      const res = await fetch(`${DAEMON_URL}/api/v1/tools/ingest`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify({ url: autoConfigUrl, type: autoConfigType })
      });
      
      const data = await res.json();
      if (res.ok && data.manifest) {
        setFormData(prev => ({ ...prev, ...data.manifest }));
        setStep(1); // Proceed to metadata to review
      } else {
        alert("Ingestion failed: " + (data.detail || "Unknown error"));
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
        body: JSON.stringify({ target_domain: formData.execution?.baseUrl })
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
           handleExecutionChange('authHeadersVaultId', data.vault_id);
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
      <div className="bg-glass-1 border border-glass-edge rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl relative overflow-hidden">
        
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
                  </select>
                  <input
                    type="text"
                    value={autoConfigUrl}
                    onChange={e => setAutoConfigUrl(e.target.value)}
                    placeholder="https://api.example.com/swagger.json"
                    className="flex-1 bg-glass-pressed border border-glass-edge rounded-xl p-3 text-sm text-text-primary focus:border-accent outline-none"
                  />
                  <button onClick={handleAutoConfig} disabled={isIngesting} className="glass-btn px-4">
                    {isIngesting ? 'Ingesting...' : <><Link className="w-4 h-4" /> Auto-Fill</>}
                  </button>
                </div>
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
                      handleExecutionChange('type', e.target.value);
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
              <div className="space-y-4">
                <h3 className="text-sm font-bold text-accent">2. Connection & Transport</h3>
                
                {formData.execution?.type === 'API' && (
                  <>
                    <div className="space-y-2">
                      <label className="text-[10px] uppercase font-mono tracking-widest text-text-secondary">Base URL</label>
                      <input
                        type="text"
                        value={formData.execution?.baseUrl || ''}
                        onChange={e => handleExecutionChange('baseUrl', e.target.value)}
                        className="w-full bg-glass-pressed border border-glass-edge rounded-xl p-3 text-sm text-text-primary"
                      />
                    </div>
                    
                    <div className="space-y-2 mt-4">
                      <label className="text-[10px] uppercase font-mono tracking-widest text-text-secondary">Authorization Type</label>
                      <select
                        value={formData.execution?.authType || 'apikey'}
                        onChange={e => handleExecutionChange('authType', e.target.value)}
                        className="w-full bg-glass-pressed border border-glass-edge rounded-xl p-3 text-sm text-text-primary"
                      >
                        <option value="apikey">API Key / Bearer Token</option>
                        <option value="oauth2">OAuth2 (Device Grant)</option>
                      </select>
                    </div>

                    {formData.execution?.authType === 'oauth2' ? (
                      <div className="p-4 bg-glass-pressed border border-glass-edge rounded-xl space-y-4">
                        <p className="text-xs text-text-secondary">
                          Leveraging RFC 8628 Device Authorization Grant for sovereign, redirection-free authentication.
                        </p>
                        {oauthDeviceState.status === 'idle' && (
                          <button onClick={initiateDeviceAuth} className="glass-btn glass-btn--primary">
                            Begin Device Authorization
                          </button>
                        )}
                        {oauthDeviceState.status === 'pending' && (
                          <div className="space-y-2">
                            <p className="text-sm text-accent">1. Visit: <a href={oauthDeviceState.verification_uri} target="_blank" rel="noreferrer" className="underline">{oauthDeviceState.verification_uri}</a></p>
                            <p className="text-sm text-accent">2. Enter Code: <strong className="text-lg text-white">{oauthDeviceState.user_code}</strong></p>
                            <p className="text-xs text-text-tertiary mt-2">Polling for token...</p>
                          </div>
                        )}
                        {oauthDeviceState.status === 'success' && (
                          <div className="flex items-center gap-2 text-green-400 text-sm">
                            <CheckCircle className="w-5 h-5" /> OAuth2 Token Securely Vaulted
                          </div>
                        )}
                        {oauthDeviceState.status === 'error' && (
                          <div className="text-red-400 text-sm">{oauthDeviceState.message}</div>
                        )}
                      </div>
                    ) : (
                      <div className="space-y-2">
                        <label className="text-[10px] uppercase font-mono tracking-widest text-text-secondary">Auth Header Secret (Vault Routed)</label>
                        <input
                          type="password"
                          placeholder={formData.execution?.authHeadersVaultId ? "•••••••••••••••• (Secured in Vault)" : "Bearer token or API Key... (Will be stored securely in Vault)"}
                          onBlur={async (e) => {
                            if (e.target.value && !e.target.value.includes('••••')) {
                              const vaultId = await handleStoreSecret(e.target.value);
                              if (vaultId) {
                                  handleExecutionChange('authHeadersVaultId', vaultId);
                                  e.target.value = "•••••••••••••••• (Secured in Vault)";
                              }
                            }
                          }}
                          className="w-full bg-glass-pressed border border-glass-edge rounded-xl p-3 text-sm text-text-primary"
                        />
                        <p className="text-[8px] text-accent">Secrets never touch the disk in plaintext. They are routed via VaultManager.</p>
                      </div>
                    )}
                  </>
                )}

                {(formData.execution?.type === 'MCP' || formData.execution?.type === 'CLI') && (
                  <>
                    {formData.execution?.type === 'MCP' && (
                      <div className="space-y-2">
                        <label className="text-[10px] uppercase font-mono tracking-widest text-text-secondary">Transport</label>
                        <select
                          value={formData.execution?.transport || 'stdio'}
                          onChange={e => handleExecutionChange('transport', e.target.value)}
                          className="w-full bg-glass-pressed border border-glass-edge rounded-xl p-3 text-sm text-text-primary"
                        >
                          <option value="stdio">stdio (Local Command)</option>
                          <option value="sse">SSE (Network)</option>
                        </select>
                      </div>
                    )}

                    {(formData.execution?.type === 'CLI' || formData.execution?.transport === 'stdio') ? (
                        <div className="space-y-2">
                          <label className="text-[10px] uppercase font-mono tracking-widest text-text-secondary">Execution Command</label>
                          <input
                              type="text"
                              value={formData.execution?.command || ''}
                              onChange={e => handleExecutionChange('command', e.target.value)}
                              className="w-full bg-glass-pressed border border-glass-edge rounded-xl p-3 text-sm text-text-primary font-mono"
                              placeholder="e.g. npx -y @modelcontextprotocol/server-postgres"
                          />
                        </div>
                    ) : (
                        <div className="space-y-2">
                          <label className="text-[10px] uppercase font-mono tracking-widest text-text-secondary">SSE URL</label>
                          <input
                              type="text"
                              value={formData.execution?.url || ''}
                              onChange={e => handleExecutionChange('url', e.target.value)}
                              className="w-full bg-glass-pressed border border-glass-edge rounded-xl p-3 text-sm text-text-primary"
                          />
                        </div>
                    )}

                    <div className="space-y-2 mt-6">
                      <label className="text-[10px] uppercase font-mono tracking-widest text-text-secondary flex items-center gap-2">
                        <Key className="w-3 h-3" /> Environment Variables (Vault Routed)
                      </label>
                      <div className="space-y-2">
                        {Object.entries(formData.execution?.envVarsVaultId || {}).map(([key, vaultId]) => (
                          <div key={key} className="flex gap-2 items-center">
                            <span className="bg-glass-3 px-3 py-2 rounded text-xs font-mono text-text-primary">{key}</span>
                            <span className="bg-glass-pressed px-3 py-2 rounded text-xs text-accent flex-1">•••••••••••••••• (Secured)</span>
                            <button onClick={() => handleRemoveEnvVar(key)} className="p-2 hover:text-red-400 text-text-tertiary">
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        ))}
                      </div>
                      <div className="flex gap-2 mt-2">
                        <input 
                          type="text" 
                          placeholder="ENV_KEY" 
                          value={envVarKey}
                          onChange={e => setEnvVarKey(e.target.value)}
                          className="w-1/3 bg-glass-pressed border border-glass-edge rounded p-2 text-xs text-text-primary font-mono outline-none"
                        />
                        <input 
                          type="password" 
                          placeholder="Secret Value..." 
                          value={envVarValue}
                          onChange={e => setEnvVarValue(e.target.value)}
                          className="flex-1 bg-glass-pressed border border-glass-edge rounded p-2 text-xs text-text-primary outline-none"
                        />
                        <button onClick={handleAddEnvVar} className="bg-glass-3 hover:bg-glass-edge px-3 rounded text-xs text-text-primary">Add</button>
                      </div>
                    </div>
                  </>
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
          <div className="w-1/3 pl-6 hidden md:block">
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