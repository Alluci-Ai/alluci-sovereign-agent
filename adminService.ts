
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
        console.warn("[ ADMIN ]: connect() called! token length: ", token ? token.length : 0);
        if (this.socket) {
            console.warn("[ ADMIN ]: Socket already exists, skipping connect.");
            return;
        }
        this.token = token;
        this.callbacks = callbacks;
        console.warn("[ ADMIN ]: Starting connect to WS_URL:", this.WS_URL);
        this._establishConnection();
    }

    private _establishConnection() {
        if (this.socket) {
            this.socket.close();
        }

        console.warn("[ ADMIN ]: Connecting to gateway at", this.WS_URL);
        this.socket = new WebSocket(this.WS_URL);

        this.socket.onopen = () => {
            console.warn("[ ADMIN ]: WebSocket Opened. Authenticating...");
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
                console.warn("[ ADMIN ]: Received msg:", msg);

                // Handle Hello response
                if (msg.id === "auth_1") {
                    if (msg.error) {
                        console.error("[ ADMIN ]: Auth failed", msg.error);
                        this.socket?.close();
                        return;
                    }
                    console.warn("[ ADMIN ]: Authenticated.");
                    this.callbacks?.onOpen?.();

                    // Subscribe to all events by default (empty list in gateway means all)
                    this.sendRPC("events.subscribe", { channels: [] });
                    return;
                }

                // Handle Events
                if (msg.method) {
                    if (msg.method === "exec.approval") {
                        this.callbacks?.onApprovalRequest?.(msg.params);
                    }
                    this.callbacks?.onSystemEvent?.(msg.method, msg.params);
                    this._notifyListeners(msg.method, msg.params);
                }

                // Handle RPC Responses
                if (msg.result !== undefined) {
                    this.callbacks?.onSystemEvent?.('rpc.response', { id: msg.id, result: msg.result });
                    this._notifyListeners('rpc.response', { id: msg.id, result: msg.result });
                }

                if (msg.error !== undefined) {
                    this.callbacks?.onSystemEvent?.('rpc.error', { id: msg.id, error: msg.error });
                    this._notifyListeners('rpc.error', { id: msg.id, error: msg.error });
                }
            } catch (e) {
                console.error("[ ADMIN ]: WS parse error", e);
            }
        };

        this.socket.onerror = (e) => {
            console.warn("[ ADMIN ]: Socket error", e);
        };

        this.socket.onclose = (event) => {
            // Prevent old sockets from triggering reconnects if disconnected
            if (this.socket && this.socket !== event.target) {
                return;
            }
            console.warn("[ ADMIN ]: Disconnected. Retrying in 5s...");
            this.callbacks?.onClose?.();
            this.reconnectTimer = setTimeout(() => this._establishConnection(), 5000);
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
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        if (this.socket) {
            this.socket.onclose = null; // PREVENT RECONNECT LOOP
            this.socket.close();
            this.socket = null;
        }
    }
}

export const adminService = new AlluciAdminService();
