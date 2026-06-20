
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { useStore } from './store/useStore';

export interface AdminCallbacks {
    onApprovalRequest?: (data: { request_id: string; command: string; tool_name: string; context: string }) => void;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onSystemEvent?: (method: string, params: any) => void;
    onOpen?: () => void;
    onClose?: () => void;
}

export class AlluciAdminService {
    private socket: WebSocket | null = null;
    private DAEMON_URL = import.meta.env.VITE_DAEMON_URL || '';
    private WS_URL = this.DAEMON_URL 
        ? this.DAEMON_URL.replace('http', 'ws') + '/ws/admin'
        : (window.location.protocol === 'https:' ? 'wss:' : 'ws:') + '//' + window.location.host + '/ws/admin';
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    private reconnectTimer: any = null;
    private token: string | null = null;
    private callbacks: AdminCallbacks | null = null;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    private eventListeners: ((method: string, params: any) => void)[] = [];

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    addListener(listener: (method: string, params: any) => void) {
        this.eventListeners.push(listener);
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    removeListener(listener: (method: string, params: any) => void) {
        this.eventListeners = this.eventListeners.filter(l => l !== listener);
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    private _notifyListeners(method: string, params: any) {
        this.eventListeners.forEach(l => l(method, params));
    }

    connect(token: string, callbacks: AdminCallbacks) {
        this.token = token;
        this.callbacks = callbacks;
        this._establishConnection();
    }

    private _establishConnection() {
        if (this.socket) {
            this.socket.close();
        }

        console.log("[ ADMIN ]: Connecting to gateway...");
        this.socket = new WebSocket(this.WS_URL);

        this.socket.onopen = () => {
            console.log("[ ADMIN ]: WebSocket Opened. Authenticating...");
            // Step 1: Send hello with token
            this.socket?.send(JSON.stringify({
                jsonrpc: "2.0",
                method: "hello",
                params: { token: this.token },
                id: "auth_1"
            }));
        };

        this.socket.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);

                // Handle Hello response
                if (msg.id === "auth_1") {
                    if (msg.error) {
                        console.error("[ ADMIN ]: Auth failed", msg.error);
                        this.socket?.close();
                        return;
                    }
                    console.info("[ ADMIN ]: Authenticated.");
                    this.callbacks?.onOpen?.();

                    // Subscribe to all events by default (empty list in gateway means all)
                    this.sendRPC("events.subscribe", { channels: [] });
                    return;
                }

                // Handle server notifications (events)
                if (msg.method) {
                    if (msg.method === "exec.approval") {
                        this.callbacks?.onApprovalRequest?.(msg.params);
                    } else if (msg.method === "hello") {
                        // Welcome message from server
                    } else {
                        this.callbacks?.onSystemEvent?.(msg.method, msg.params);
                    }
                    this._notifyListeners(msg.method, msg.params);
                }

                // Handle RPC results
                if (msg.result !== undefined) {
                    this.callbacks?.onSystemEvent?.('rpc.response', { id: msg.id, result: msg.result });
                    this._notifyListeners('rpc.response', { id: msg.id, result: msg.result });
                }

                if (msg.error !== undefined) {
                    this.callbacks?.onSystemEvent?.('rpc.error', { id: msg.id, error: msg.error });
                    this._notifyListeners('rpc.error', { id: msg.id, error: msg.error });
                }
            } catch (e) {
                console.error("[ ADMIN ]: Parse error", e);
            }
        };

        this.socket.onclose = () => {
            console.warn("[ ADMIN ]: Disconnected. Retrying in 5s...");
            this.callbacks?.onClose?.();
            this.reconnectTimer = setTimeout(() => this._establishConnection(), 5000);
        };

        this.socket.onerror = (err) => {
            console.error("[ ADMIN ]: Socket error", err);
        };
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    sendRPC(method: string, params: any = {}) {
        if (this.socket?.readyState === WebSocket.OPEN) {
            const id = Math.random().toString(36).substring(7);
            this.socket.send(JSON.stringify({
                jsonrpc: "2.0",
                method,
                params,
                id
            }));
            return id;
        }
        return null;
    }

    disconnect() {
        if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
        this.socket?.close();
        this.socket = null;
    }
}

export const adminService = new AlluciAdminService();
