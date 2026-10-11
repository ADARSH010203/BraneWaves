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
            credentials: "include",
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
                    credentials: "include",
                });
                if (!retryRes.ok) throw new ApiError(retryRes.status, await retryRes.text());
                return retryRes.json();
            }
            throw new ApiError(401, "Unauthorized");
        }

        

        if (!res.ok) {
            let errorMsg = `Request failed with status ${res.status}`;
            try {
                const bodyText = await res.text();
                try {
                    const json = JSON.parse(bodyText);
                    if (typeof json.detail === "string") {
                        errorMsg = json.detail;
                    } else if (Array.isArray(json.detail)) {
                        errorMsg = json.detail.map((e: any) => e.msg || JSON.stringify(e)).join(", ");
                    } else if (json.message) {
                        errorMsg = json.message;
                    } else {
                        errorMsg = bodyText;
                    }
                } catch {
                    if (bodyText) errorMsg = bodyText;
                }
            } catch {
                // Ignore
            }
            throw new ApiError(res.status, errorMsg);
        }

        return res.json();
    }

    private async refreshToken(): Promise<boolean> {
        try {
            const res = await fetch(`${this.baseUrl}/auth/refresh`, {
                method: "POST",
                credentials: "include",
            });
            if (!res.ok) return false;
            const data = await res.json();
            localStorage.setItem("arc_access_token", data.access_token);
            localStorage.removeItem("arc_refresh_token");
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

    async logout() {
        try {
            await fetch(`${this.baseUrl}/auth/logout`, {
                method: "POST",
                credentials: "include",
            });
        } catch {
            // Ignore network errors on logout
        } finally {
            if (typeof window !== "undefined") {
                localStorage.removeItem("arc_access_token");
                localStorage.removeItem("arc_refresh_token");
                localStorage.removeItem("arc_user");
            }
        }
    }

    // ── Tasks ─────────────────────────────────────────────────────────
    async getTemplates() {
        return this.request<any>("/templates");
    }

    async createTask(
        title: string,
        description: string,
        budget_usd?: number,
        tags?: string[],
        use_knowledge_base = true,
        selected_file_ids: string[] = [],
    ) {
        return this.request<any>("/tasks", {
            method: "POST",
            body: JSON.stringify({
                title,
                description,
                budget_usd,
                tags: tags || [],
                use_knowledge_base,
                selected_file_ids,
            }),
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
            credentials: "include",
        });
        if (!res.ok) throw new ApiError(res.status, await res.text());
        return res.json();
    }

    // ── Knowledge Base (FEAT-10) ──────────────────────────────────────
    async uploadKBFile(file: File) {
        const formData = new FormData();
        formData.append("file", file);
        const token = this.getToken();
        const res = await fetch(`${this.baseUrl}/knowledge-base/upload`, {
            method: "POST",
            headers: token ? { Authorization: `Bearer ${token}` } : {},
            body: formData,
            credentials: "include",
        });
        if (!res.ok) throw new ApiError(res.status, await res.text());
        return res.json();
    }

    async getKBDocuments() {
        return this.request<any>("/knowledge-base");
    }

    async deleteKBDocument(id: string) {
        return this.request<any>(`/knowledge-base/${id}`, { method: "DELETE" });
    }

    // ── Report Export (FEAT-01) ───────────────────────────────────────
    async exportReport(taskId: string, format: "pdf" | "docx"): Promise<void> {
        const token = this.getToken();
        const res = await fetch(
            `${this.baseUrl}/tasks/${taskId}/export?format=${format}`,
            {
                headers: token ? { Authorization: `Bearer ${token}` } : {},
                credentials: "include",
            }
        );
        if (!res.ok) {
            const body = await res.text();
            throw new ApiError(res.status, body);
        }

        // Trigger browser download from blob
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;

        // Extract filename from Content-Disposition or use default
        const disposition = res.headers.get("Content-Disposition");
        let filename = `report.${format}`;
        if (disposition) {
            const match = disposition.match(/filename="?([^"]+)"?/);
            if (match) filename = match[1];
        }
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    }

    // ── Task Cancellation (FEAT-02) ──────────────────────────────────
    async cancelTask(taskId: string) {
        return this.request<{ success: boolean; message: string }>(
            `/tasks/${taskId}/cancel`,
            { method: "POST" }
        );
    }

    // ── Report Chat (FEAT-07) ────────────────────────────────────────
    async chatWithReport(taskId: string, message: string) {
        return this.request<{ reply: string }>(`/tasks/${taskId}/chat`, {
            method: "POST",
            body: JSON.stringify({ message }),
        });
    }

    // ── Analytics (FEAT-06) ──────────────────────────────────────────
    async getCostAnalytics() {
        return this.request<any>("/analytics/costs");
    }

    // ── Memory Graph (ARC Brain) ────────────────────────────────────
    async getMemoryGraph() {
        return this.request<{
            nodes: Array<{ id: string; label: string; type: string; description: string; task_count: number; occurrence_count: number }>;
            edges: Array<{ id: string; from: string; to: string; weight: number }>;
            total_nodes: number;
            total_edges: number;
        }>("/memory/graph");
    }

    async searchMemory(query: string) {
        return this.request<{ results: Array<{ label: string; description: string; task_ids: string[]; score: number }> }>(
            `/memory/search?query=${encodeURIComponent(query)}`
        );
    }

    async deleteMemoryNode(nodeId: string) {
        return this.request<{ success: boolean }>(`/memory/${nodeId}`, { method: "DELETE" });
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
