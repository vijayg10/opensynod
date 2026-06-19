/**
 * SSE client that wraps EventSource with auto-reconnect and
 * since_message_id replay support.
 *
 * Accepts either a static token string or a getter function that returns
 * the current token (so reconnects always use a fresh token after refresh).
 */

export type SSEEventHandler = (event: MessageEvent) => void;
export type TokenGetter = () => string | null;

export class SSEClient {
  private _url: string;
  private _getToken: TokenGetter;
  private _onTokenExpired?: () => Promise<string | null>;
  private _lastMessageId: string | null = null;
  private _es: EventSource | null = null;
  private _handlers: Map<string, Set<SSEEventHandler>> = new Map();
  private _closed = false;
  private _consecutiveErrors = 0;

  constructor(
    url: string,
    tokenOrGetter: string | TokenGetter,
    options?: { onTokenExpired?: () => Promise<string | null> },
  ) {
    this._url = url;
    this._getToken =
      typeof tokenOrGetter === "function" ? tokenOrGetter : () => tokenOrGetter;
    this._onTokenExpired = options?.onTokenExpired;
  }

  on(eventType: string, handler: SSEEventHandler): void {
    if (!this._handlers.has(eventType)) {
      this._handlers.set(eventType, new Set());
    }
    this._handlers.get(eventType)!.add(handler);
  }

  off(eventType: string, handler: SSEEventHandler): void {
    this._handlers.get(eventType)?.delete(handler);
  }

  connect(): void {
    this._closed = false;
    this._openEventSource();
  }

  close(): void {
    this._closed = true;
    this._es?.close();
    this._es = null;
  }

  private _buildUrl(): string {
    const token = this._getToken();
    const params = new URLSearchParams();
    if (token) params.set("token", token);
    if (this._lastMessageId) {
      params.set("since_message_id", this._lastMessageId);
    }
    return `${this._url}?${params.toString()}`;
  }

  private _openEventSource(): void {
    if (this._closed) return;
    this._es = new EventSource(this._buildUrl());

    this._es.onopen = () => {
      this._consecutiveErrors = 0;
    };

    this._es.onerror = () => {
      this._es?.close();
      if (this._closed) return;
      this._consecutiveErrors++;

      // After 2 consecutive errors, try refreshing the token before reconnecting
      if (this._consecutiveErrors >= 2 && this._onTokenExpired) {
        this._onTokenExpired().then(() => {
          if (!this._closed) {
            setTimeout(() => this._openEventSource(), 1000);
          }
        });
      } else {
        setTimeout(() => this._openEventSource(), 3000);
      }
    };

    // Register all known event types
    for (const [eventType] of this._handlers) {
      this._es.addEventListener(eventType, (e) => {
        if (e instanceof MessageEvent) {
          const data = JSON.parse(e.data);
          if (data.message_id) {
            this._lastMessageId = data.message_id;
          }
          this._handlers.get(eventType)?.forEach((h) => h(e));
        }
      });
    }
  }
}
