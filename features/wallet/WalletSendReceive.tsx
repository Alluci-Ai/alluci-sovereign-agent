import React, { useState, useEffect } from 'react';
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { Send, Download, RefreshCcw, Activity, ShieldCheck, DollarSign, Database, Zap, AlertTriangle } from 'lucide-react';
import { useStore } from '../../store/useStore';
import { WalletInvoice } from './WalletInvoice';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://127.0.0.1:8000';

interface WalletSendReceiveProps {
    onTransactionComplete: () => void;
}

export const WalletSendReceive: React.FC<WalletSendReceiveProps> = ({ onTransactionComplete }) => {
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { accessToken, walletMode } = useStore();
    const [activeTab, setActiveTab] = useState<'send' | 'receive' | 'convert'>('send');

    // SEND STATE
    const [address, setAddress] = useState('');
    const [amount, setAmount] = useState('');
    const [currency, setCurrency] = useState('VRSC');
    const [memo, setMemo] = useState('');

    // CONVERT STATE
    const [convAmount, setConvAmount] = useState('');
    const [convFrom, setConvFrom] = useState('VRSC');
    const [convTo, setConvTo] = useState('vETH');
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const [convVia, setConvVia] = useState('Bridge.vETH');
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const [convEstimate, setConvEstimate] = useState<any>(null);
    const [estimating, setEstimating] = useState(false);

    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<{ success?: boolean; error?: string; txid?: string } | null>(null);
    const [knownCurrencies, setKnownCurrencies] = useState<string[]>(['VRSC', 'vETH', 'DAI.vETH', 'MKR.vETH', 'Bridge.vETH']);

    useEffect(() => {
        fetchCurrencies();
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [accessToken]);

    useEffect(() => {
        if (activeTab === 'convert' && convAmount && !isNaN(parseFloat(convAmount)) && parseFloat(convAmount) > 0) {
            const timer = setTimeout(() => fetchEstimate(), 1000);
            return () => clearTimeout(timer);
        } else {
            setConvEstimate(null);
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [convAmount, convFrom, convTo, convVia]);

    const fetchEstimate = async () => {
        setEstimating(true);
        try {
            const res = await fetch(`${DAEMON_URL}/api/v1/wallet/convert/estimate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${accessToken}`
                },
                body: JSON.stringify({
                    amount: parseFloat(convAmount),
                    from_currency: convFrom,
                    to_currency: convTo,
                    via: convVia || null
                })
            });
            const data = await res.json();
            if (res.ok && !data.error) {
                setConvEstimate(data);
            } else {
                setConvEstimate(null);
            }
        } catch (e) {
            setConvEstimate(null);
        } finally {
            setEstimating(false);
        }
    };

    const fetchCurrencies = async () => {
        try {
            const res = await fetch(`${DAEMON_URL}/api/v1/wallet/currencies`, {
                headers: { 'Authorization': `Bearer ${accessToken}` }
            });
            if (res.ok) {
                const data = await res.json();
                if (data && data.length > 0) {
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    setKnownCurrencies(data.map((c: any) => c.name));
                }
            }
        } catch (e) { console.error(e); }
    };

    const handleSend = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setResult(null);

        try {
            const res = await fetch(`${DAEMON_URL}/api/v1/wallet/send`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${accessToken}`
                },
                body: JSON.stringify({
                    to: address,
                    amount: parseFloat(amount),
                    currency,
                    memo
                })
            });

            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Send failed');

            setResult({ success: true, txid: data.txid });
            setAddress('');
            setAmount('');
            setMemo('');
            onTransactionComplete();
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        } catch (err: any) {
            setResult({ success: false, error: err.message });
        } finally {
            setLoading(false);
        }
    };

    const handleConvert = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setResult(null);

        try {
            const res = await fetch(`${DAEMON_URL}/api/v1/wallet/convert`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${accessToken}`
                },
                body: JSON.stringify({
                    amount: parseFloat(convAmount),
                    from_currency: convFrom,
                    to_currency: convTo,
                    via: convVia || null
                })
            });

            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Conversion failed');

            setResult({ success: true, txid: data.txid });
            setConvAmount('');
            onTransactionComplete();
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        } catch (err: any) {
            setResult({ success: false, error: err.message });
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="glass-panel p-6 flex flex-col h-[460px] border-white/5 bg-white/[0.02]">
            <div className="flex border-b border-white/5 gap-8 mb-6 relative">
                <button
                    onClick={() => setActiveTab('send')}
                    className={`pb-3 font-bold text-[10px] uppercase tracking-widest transition-all ${activeTab === 'send' ? 'text-accent border-b-2 border-accent' : 'text-text-tertiary hover:text-text-secondary border-b-2 border-transparent'}`}
                >
                    <span className="flex items-center gap-2"><Send size={14} /> Send Assets</span>
                </button>
                <button
                    onClick={() => setActiveTab('receive')}
                    className={`pb-3 font-bold text-[10px] uppercase tracking-widest transition-all ${activeTab === 'receive' ? 'text-status-success border-b-2 border-status-success' : 'text-text-tertiary hover:text-text-secondary border-b-2 border-transparent'}`}
                >
                    <span className="flex items-center gap-2"><Download size={14} /> VerusPay Invoice</span>
                </button>
                <button
                    onClick={() => setActiveTab('convert')}
                    className={`pb-3 font-bold text-[10px] uppercase tracking-widest transition-all ${activeTab === 'convert' ? 'text-indigo-400 border-b-2 border-indigo-400' : 'text-text-tertiary hover:text-text-secondary border-b-2 border-transparent'}`}
                >
                    <span className="flex items-center gap-2"><RefreshCcw size={14} /> PBaaS Converter</span>
                </button>
            </div>

            <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
                {activeTab === 'send' && (
                    <form onSubmit={handleSend} className="space-y-6 animate-in fade-in slide-in-from-left-2 duration-300">
                        <div className="space-y-4">
                            <div>
                                <label className="block text-[10px] font-bold text-text-tertiary uppercase tracking-widest mb-2 ml-1">Recipient Key</label>
                                <input
                                    type="text"
                                    value={address}
                                    onChange={(e) => setAddress(e.target.value)}
                                    placeholder="R-address, i-address, or VerusID@"
                                    className="glass-input w-full p-3 bg-black/20 text-text-primary text-xs font-mono placeholder-text-muted border-white/5 focus:border-accent/40"
                                    required
                                />
                            </div>

                            <div className="grid grid-cols-5 gap-4">
                                <div className="col-span-3">
                                    <label className="block text-[10px] font-bold text-text-tertiary uppercase tracking-widest mb-2 ml-1">Transfer Amount</label>
                                    <div className="relative group">
                                        <input
                                            type="number"
                                            step="0.00000001"
                                            min="0"
                                            value={amount}
                                            onChange={(e) => setAmount(e.target.value)}
                                            placeholder="0.00000000"
                                            className="glass-input w-full p-3 bg-black/20 text-text-primary text-xs font-mono border-white/5 focus:border-accent/40"
                                            required
                                        />
                                        <button
                                            type="button"
                                            className="absolute right-2 top-1/2 -translate-y-1/2 text-[9px] font-bold text-accent bg-accent/10 px-2 py-1 rounded border border-accent/20 hover:bg-accent/20 transition-all opacity-0 group-hover:opacity-100 uppercase tracking-widest"
                                        >MAX</button>
                                    </div>
                                </div>
                                <div className="col-span-2">
                                    <label className="block text-[10px] font-bold text-text-tertiary uppercase tracking-widest mb-2 ml-1">Asset</label>
                                    <select
                                        className="glass-input w-full p-3 bg-black/20 text-text-primary text-xs font-bold appearance-none border-white/5 cursor-pointer"
                                        value={currency}
                                        onChange={(e) => setCurrency(e.target.value)}
                                    >
                                        {knownCurrencies.map(c => <option key={c} value={c} className="bg-surface-elevated">{c}</option>)}
                                    </select>
                                </div>
                            </div>

                            <div>
                                <label className="block text-[10px] font-bold text-text-tertiary uppercase tracking-widest mb-2 ml-1">Private Memo</label>
                                <input
                                    type="text"
                                    value={memo}
                                    onChange={(e) => setMemo(e.target.value)}
                                    placeholder="Optional cryptographically signed memo"
                                    className="glass-input w-full p-3 bg-black/20 text-text-secondary text-xs border-white/5 focus:border-accent/40"
                                />
                            </div>
                        </div>

                        <div className="pt-2">
                            <button
                                type="submit"
                                disabled={loading}
                                className={`glass-btn w-full py-4 bg-accent/10 border-accent/30 text-accent font-bold uppercase tracking-[0.2em] text-xs hover:bg-accent/20 transition-all shadow-[0_4px_16px_rgba(56,189,248,0.1)] ${loading ? 'opacity-50 cursor-wait' : ''}`}
                            >
                                {loading ? 'Broadcasting Tx...' : `Execute Transfer`}
                            </button>
                        </div>

                        {result?.success && (
                            <div className="p-4 bg-status-success/5 border border-status-success/20 rounded-xl mt-4 animate-in zoom-in-95 duration-500">
                                <div className="text-[10px] font-bold text-status-success uppercase tracking-widest mb-2">Network Confirmation Pending</div>
                                <div className="text-[11px] font-mono text-text-secondary break-all bg-black/40 p-2 rounded border border-white/5 select-all">
                                    {result.txid}
                                </div>
                            </div>
                        )}
                        {result?.error && (
                            <div className="p-4 bg-status-error/5 border border-status-error/20 rounded-xl mt-4 text-[11px] font-medium text-status-error flex items-start gap-3">
                                <AlertTriangle size={16} className="shrink-0" />
                                <div>
                                    <span className="font-bold block uppercase tracking-widest text-[9px] mb-1">Execution Failure</span>
                                    {result.error}
                                </div>
                            </div>
                        )}
                    </form>
                )}

                {activeTab === 'receive' && (
                    <div className="animate-in fade-in slide-in-from-right-2 duration-300 h-full">
                        <WalletInvoice />
                    </div>
                )}

                {activeTab === 'convert' && (
                    <form onSubmit={handleConvert} className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
                        <div className="p-4 border border-indigo-500/20 rounded-xl bg-indigo-500/5 relative overflow-hidden">
                            <div className="absolute top-0 right-0 p-4 opacity-[0.03] pointer-events-none">
                                <RefreshCcw size={80} className="text-indigo-400" />
                            </div>
                            <h3 className="text-indigo-400 font-bold text-[10px] uppercase tracking-widest mb-1.5 flex items-center gap-2">
                                <Zap size={14} /> PBaaS Automated Market Maker
                            </h3>
                            <p className="text-[10px] text-text-tertiary leading-relaxed max-w-[85%]">
                                Utilize protocol-level liquidity baskets for MEV-resistant conversions. Settlement occurs at the block level without front-running.
                            </p>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div className="col-span-2">
                                <label className="block text-[10px] font-bold text-text-tertiary uppercase tracking-widest mb-2 ml-1">Input Amount</label>
                                <input
                                    type="number"
                                    step="0.00000001"
                                    min="0"
                                    value={convAmount}
                                    onChange={(e) => setConvAmount(e.target.value)}
                                    placeholder="0.00000000"
                                    className="glass-input w-full p-3 bg-black/20 text-text-primary text-xs font-mono border-indigo-500/20 focus:border-indigo-500/40"
                                    required
                                />
                            </div>
                            <div>
                                <label className="block text-[10px] font-bold text-text-tertiary uppercase tracking-widest mb-2 ml-1">Source</label>
                                <select
                                    className="glass-input w-full p-3 bg-black/20 text-text-primary text-xs font-bold appearance-none border-white/5 cursor-pointer"
                                    value={convFrom}
                                    onChange={(e) => setConvFrom(e.target.value)}
                                >
                                    {knownCurrencies.map(c => <option key={c} value={c} className="bg-surface-elevated">{c}</option>)}
                                </select>
                            </div>
                            <div>
                                <label className="block text-[10px] font-bold text-indigo-400 uppercase tracking-widest mb-2 ml-1">Target</label>
                                <select
                                    className="glass-input w-full p-3 bg-black/20 text-text-primary text-xs font-bold appearance-none border-indigo-500/20 cursor-pointer"
                                    value={convTo}
                                    onChange={(e) => setConvTo(e.target.value)}
                                >
                                    {knownCurrencies.map(c => <option key={c} value={c} className="bg-surface-elevated">{c}</option>)}
                                </select>
                            </div>
                        </div>

                        {convEstimate && !estimating && (
                            <div className="p-4 bg-white/[0.03] border border-white/5 rounded-xl flex items-center justify-between animate-in zoom-in-95">
                                <div className="flex items-center gap-3">
                                    <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
                                        <Activity size={14} />
                                    </div>
                                    <div>
                                        <span className="text-[10px] font-bold text-text-tertiary uppercase tracking-wider block">Estimated Return</span>
                                        <span className="text-xs font-mono text-text-primary">
                                            {convEstimate.estimated_return.toFixed(8)} {convTo}
                                        </span>
                                    </div>
                                </div>
                                <span className="text-[8px] font-bold text-indigo-400 bg-indigo-400/10 px-1.5 py-0.5 rounded uppercase tracking-widest">Optimal Route</span>
                            </div>
                        )}

                        <button
                            type="submit"
                            disabled={loading || !convAmount}
                            className={`glass-btn w-full py-4 bg-indigo-500/10 border-indigo-500/30 text-indigo-400 font-bold uppercase tracking-[0.2em] text-xs hover:bg-indigo-500/20 transition-all shadow-[0_4px_16px_rgba(129,140,248,0.1)] ${loading || !convAmount ? 'opacity-50 cursor-not-allowed' : ''}`}
                        >
                            {loading ? 'Routing DeFi Call...' : `Finalize Conversion`}
                        </button>

                        {result?.success && (
                            <div className="p-4 bg-status-success/5 border border-status-success/20 rounded-xl mt-4 animate-in zoom-in-95 duration-500">
                                <div className="text-[10px] font-bold text-status-success uppercase tracking-widest mb-2">Conversion Broadcasted</div>
                                <div className="text-[11px] font-mono text-text-secondary break-all bg-black/40 p-2 rounded border border-white/5 select-all">
                                    {result.txid}
                                </div>
                            </div>
                        )}
                        {result?.error && (
                            <div className="p-4 bg-status-error/5 border border-status-error/20 rounded-xl mt-4 text-[11px] font-medium text-status-error flex items-start gap-3">
                                <AlertTriangle size={16} className="shrink-0" />
                                <div>
                                    <span className="font-bold block uppercase tracking-widest text-[9px] mb-1">Conversion Error</span>
                                    {result.error}
                                </div>
                            </div>
                        )}
                    </form>
                )}
            </div>
        </div>
    );
};
