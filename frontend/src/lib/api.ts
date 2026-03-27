/* ─── ARC Platform — API Client ──────────────────────────────────── */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiClient {
    private baseUrl: string;

    constructor(baseUrl: string) {
        this.baseUrl = baseUrl;
    }

    private getToken(): string | null {
        if (typeof window === "undefined") return null;
        return localStorage.getItem("arc_access_token");
    }

    private async request<T>(
        path: string,
        options: RequestInit = {}
    ): Promise<T> {
        const token = this.getToken();
        const headers: HeadersInit = {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
            ...(options.headers || {}),
        };

        const res = await fetch(`${this.baseUrl}${path}`, {
            ...options,
            headers,
        });

        if (res.status === 401) {
            // Try refresh
            const refreshed = await this.refreshToken();
            if (refreshed) {
                const newToken = this.getToken();
                const retryHeaders: HeadersInit = {
                    ...headers,
                    Authorization: `Bearer ${newToken}`,
                };
                const retryRes = await fetch(`${this.baseUrl}${path}`, {
                    ...options,
                    headers: retryHeaders,
                });
                if (!retryRes.ok) throw new ApiError(retryRes.status, await retryRes.text());
                return retryRes.json();
            }
            throw new ApiError(401, "Unauthorized");
        }

        if (!res.ok) {
            const body = await res.text();
            throw new ApiError(res.status, body);
        }

        return res.json();
    }

    private async refreshToken(): Promise<boolean> {
        const refreshToken = localStorage.getItem("arc_refresh_token");
        if (!refreshToken) return false;

        try {
            const res = await fetch(`${this.baseUrl}/auth/refresh`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ refresh_token: refreshToken }),
            });
            if (!res.ok) return false;
            const data = await res.json();
            localStorage.setItem("arc_access_token", data.access_token);
            localStorage.setItem("arc_refresh_token", data.refresh_token);
            return true;
        } catch {
            return false;
        }
    }

    // ── Auth ──────────────────────────────────────────────────────────
    async register(email: string, password: string, name: string) {
        return this.request<any>("/auth/register", {
            method: "POST",
            body: JSON.stringify({ email, password, name }),
        });
    }

    async login(email: string, password: string) {
        return this.request<any>("/auth/login", {
            method: "POST",
            body: JSON.stringify({ email, password }),
        });
    }

    // ── Tasks ─────────────────────────────────────────────────────────
    async createTask(title: string, description: string, budget_usd?: number, tags?: string[]) {
        return this.request<any>("/tasks", {
            method: "POST",
            body: JSON.stringify({ title, description, budget_usd, tags: tags || [] }),
        });
    }

    async getTasks(page = 1, pageSize = 20, status?: string) {
        const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
        if (status) params.set("status_filter", status);
        return this.request<any>(`/tasks?${params}`);
    }

    async getTask(taskId: string) {
        return this.request<any>(`/tasks/${taskId}`);
    }

    async getTaskSteps(taskId: string) {
        return this.request<any>(`/tasks/${taskId}/steps`);
    }

    async getTaskResult(taskId: string) {
        return this.request<any>(`/tasks/${taskId}/result`);
    }

    // ── Files ─────────────────────────────────────────────────────────
    async uploadFile(file: File, taskId?: string) {
        const formData = new FormData();
        formData.append("file", file);
        if (taskId) formData.append("task_id", taskId);

        const token = this.getToken();
        const res = await fetch(`${this.baseUrl}/files/upload`, {
            method: "POST",
            headers: token ? { Authorization: `Bearer ${token}` } : {},
            body: formData,
        });
        if (!res.ok) throw new ApiError(res.status, await res.text());
        return res.json();
    }
}

export class ApiError extends Error {
    status: number;
    constructor(status: number, message: string) {
        super(message);
        this.status = status;
        this.name = "ApiError";
    }
}

export const api = new ApiClient(API_URL);
