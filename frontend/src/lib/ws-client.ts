/**
 * WebSocket client with auth handshake, reconnect, and heartbeat.
 */

export type WSMessageHandler = (data: unknown) => void;

export class WSClient {
  private _url: string;
  private _token: string;
  private _ws: WebSocket | null = null;
  private _handlers: Map<string, Set<WSMessageHandler>> = new Map();
  private _closed = false;
  private _heartbeatTimer: ReturnType<typeof setInterval> | null = null;

  constructor(url: string, token: string) {
    this._url = url;
    this._token = token;
  }

  on(messageType: string, handler: WSMessageHandler): void {
    if (!this._handlers.has(messageType)) {
      this._handlers.set(messageType, new Set());
    }
    this._handlers.get(messageType)!.add(handler);
  }

  off(messageType: string, handler: WSMessageHandler): void {
    this._handlers.get(messageType)?.delete(handler);
  }

  connect(): void {
    this._closed = false;
    this._open();
  }

  send(type: string, payload: Record<string, unknown>): void {
    if (this._ws?.readyState === WebSocket.OPEN) {
      this._ws.send(JSON.stringify({ type, ...payload }));
    }
  }

  close(): void {
    this._closed = true;
    this._stopHeartbeat();
    this._ws?.close();
    this._ws = null;
  }

  private _open(): void {
    if (this._closed) return;
    this._ws = new WebSocket(this._url);

    this._ws.onopen = () => {
      this.send("auth", { token: this._token });
      this._startHeartbeat();
    };

    this._ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data as string);
        const type = data.type as string | undefined;
        if (type) {
          this._handlers.get(type)?.forEach((h) => h(data));
        }
      } catch {
        // ignore malformed messages
      }
    };

    this._ws.onerror = () => {
      this._stopHeartbeat();
    };

    this._ws.onclose = () => {
      this._stopHeartbeat();
      if (!this._closed) {
        setTimeout(() => this._open(), 3000);
      }
    };
  }

  private _startHeartbeat(): void {
    this._heartbeatTimer = setInterval(() => {
      this.send("presence_ping", {});
    }, 30_000);
  }

  private _stopHeartbeat(): void {
    if (this._heartbeatTimer !== null) {
      clearInterval(this._heartbeatTimer);
      this._heartbeatTimer = null;
    }
  }
}
