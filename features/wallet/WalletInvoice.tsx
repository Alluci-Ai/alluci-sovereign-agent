import React, { useState, useEffect } from 'react';
import { QrCode } from 'lucide-react';
import { useStore } from '../../store/useStore';
import { QRCodeCanvas } from 'qrcode.react';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';

export const WalletInvoice: React.FC = () => {
    const { accessToken } = useStore();

    const [invAddress, setInvAddress] = useState('');
    const [invAmount, setInvAmount] = useState('');
    const [invCurrency, setInvCurrency] = useState('VRSC');
    const [invMemo, setInvMemo] = useState('');

    const [loading, setLoading] = useState(false);
    const [knownCurrencies, setKnownCurrencies] = useState<string[]>(['VRSC', 'vETH', 'DAI.vETH', 'MKR.vETH', 'Bridge.vETH']);

    useEffect(() => {
        handleGenerateAddress();
        fetchCurrencies();
    }, [accessToken]);

    const fetchCurrencies = async () => {
        try {
            const res = await fetch(`${DAEMON_URL}/api/wallet/currencies`, {
                headers: { 'Authorization': `Bearer ${accessToken}` }
            });
            if (res.ok) {
                const data = await res.json();
                if (data && data.length > 0) {
                    setKnownCurrencies(data.map((c: any) => c.name));
                }
            }
        } catch (e) { console.error(e); }
    };

    const handleGenerateAddress = async () => {
        setLoading(true);
        try {
            const res = await fetch(`${DAEMON_URL}/api/wallet/address/new`, {
                headers: { 'Authorization': `Bearer ${accessToken}` }
            });
            const data = await res.json();
            if (data.address) {
                setInvAddress(data.address);
            }
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const generateInvoiceUri = () => {
        if (!invAddress) return '';
        let uri = `verus:${invAddress}`;
        const params = [];
        if (invAmount) params.push(`amount=${invAmount}`);
        if (invCurrency !== 'VRSC') params.push(`currency=${invCurrency}`);
        if (invMemo) params.push(`memo=${encodeURIComponent(invMemo)}`);
        if (params.length > 0) uri += `?${params.join('&')}`;
        return uri;
    };

    return (
        <div className="flex gap-6 h-full p-4">
            {/* QR Code Side */}
            <div className="flex flex-col items-center justify-center flex-[1] space-y-4 bg-surface-base/20 rounded-lg p-4 border border-border/30">
                {invAddress ? (
                    <div className="p-3 bg-white rounded-xl shadow-[0_0_20px_rgba(255,255,255,0.1)]">
                        <QRCodeCanvas value={generateInvoiceUri()} size={140} level={"H"} />
                    </div>
                ) : (
                    <div className="w-[140px] h-[140px] bg-surface-base/60 rounded-xl animate-pulse flex items-center justify-center text-text-tertiary border border-border/30">
                        <QrCode size={32} />
                    </div>
                )}
                <button
                    onClick={handleGenerateAddress}
                    disabled={loading}
                    className="text-[10px] font-medium uppercase tracking-wider text-text-tertiary hover:text-text-secondary transition-colors"
                >
                    {loading ? 'Generating...' : 'New Address'}
                </button>
            </div>

            {/* Invoice Form Side */}
            <div className="flex-[2] space-y-3 flex flex-col justify-center">
                <div className="relative group">
                    <label className="block text-[10px] font-medium text-text-tertiary uppercase tracking-wider mb-1">Receive Address</label>
                    <input
                        readOnly
                        value={invAddress || "Generating..."}
                        className="glass-input w-full p-2 text-xs font-mono text-text-primary bg-surface-base/60 border-status-success/30"
                    />
                    <div className="absolute inset-x-0 bottom-0 h-8 bg-status-success/10 backdrop-blur-[2px] opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center cursor-pointer rounded-b border-t border-status-success/30" onClick={() => {
                        if (invAddress) navigator.clipboard.writeText(invAddress);
                    }}>
                        <span className="text-[10px] font-bold text-status-success uppercase tracking-wider">Copy Address</span>
                    </div>
                </div>

                <div className="flex gap-2">
                    <div className="flex-[2]">
                        <label className="block text-[10px] font-medium text-text-tertiary uppercase tracking-wider mb-1">Request Amount</label>
                        <input
                            type="number"
                            placeholder="Any"
                            value={invAmount}
                            onChange={e => setInvAmount(e.target.value)}
                            className="glass-input w-full p-2 text-xs font-mono bg-surface-base/50"
                        />
                    </div>
                    <div className="flex-[1]">
                        <label className="block text-[10px] font-medium text-text-tertiary uppercase tracking-wider mb-1">Currency</label>
                        <select
                            className="glass-input w-full p-2 text-xs font-medium appearance-none bg-surface-base/50"
                            value={invCurrency}
                            onChange={e => setInvCurrency(e.target.value)}
                        >
                            {knownCurrencies.map(c => <option key={c} value={c}>{c}</option>)}
                        </select>
                    </div>
                </div>

                <div>
                    <label className="block text-[10px] font-medium text-text-tertiary uppercase tracking-wider mb-1">Message / Memo</label>
                    <input
                        type="text"
                        placeholder="Optional VerusPay memo"
                        value={invMemo}
                        onChange={e => setInvMemo(e.target.value)}
                        className="glass-input w-full p-2 text-xs bg-surface-base/50"
                    />
                </div>
                <div className="pt-2 text-[10px] text-text-tertiary leading-relaxed border-t border-border/30 mt-2">
                    QR updates automatically. Scan with Verus Mobile for instant settlement.
                </div>
            </div>
        </div>
    );
};
