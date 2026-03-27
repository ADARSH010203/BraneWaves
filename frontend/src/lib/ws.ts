/* ─── ARC Platform — WebSocket Client ─────────────────────────────── */
import type { WSEvent } from "@/types";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

export class TaskWebSocket {
    private ws: WebSocket | null = null;
    private taskId: string;
    private token: string;
    private listeners: ((event: WSEvent) => void)[] = [];
    private reconnectAttempts = 0;
    private maxReconnects = 5;

    constructor(taskId: string, token: string) {
        this.taskId = taskId;
        this.token = token;
    }

    connect(): void {
        this.ws = new WebSocket(`${WS_URL}/tasks/${this.taskId}/stream`);

        this.ws.onopen = () => {
            this.reconnectAttempts = 0;
            // Send auth token
            this.ws?.send(JSON.stringify({ token: this.token }));
        };

        this.ws.onmessage = (event) => {
            try {
                const data: WSEvent = JSON.parse(event.data);
                this.listeners.forEach((fn) => fn(data));
            } catch (e) {
                console.error("WS parse error:", e);
            }
        };

        this.ws.onclose = () => {
            if (this.reconnectAttempts < this.maxReconnects) {
                this.reconnectAttempts++;
                setTimeout(() => this.connect(), 1000 * this.reconnectAttempts);
            }
        };

        this.ws.onerror = (err) => {
            console.error("WS error:", err);
        };
    }

    onEvent(listener: (event: WSEvent) => void): () => void {
        this.listeners.push(listener);
        return () => {
            this.listeners = this.listeners.filter((l) => l !== listener);
        };
    }

    disconnect(): void {
        this.maxReconnects = 0;
        this.ws?.close();
        this.ws = null;
        this.listeners = [];
    }
}
