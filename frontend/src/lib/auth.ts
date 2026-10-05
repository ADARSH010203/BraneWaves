/* ─── ARC Platform — Auth Utilities ───────────────────────────────── */
import type { User } from "@/types";

export function setTokens(access: string): void {
    localStorage.setItem("arc_access_token", access);
    // Clean up refresh tokens stored by older builds. Refresh credentials now live
    // only in an HttpOnly cookie issued by the backend.
    localStorage.removeItem("arc_refresh_token");
}

export function getAccessToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("arc_access_token");
}

export function clearTokens(): void {
    localStorage.removeItem("arc_access_token");
    localStorage.removeItem("arc_refresh_token");
    localStorage.removeItem("arc_user");
}

export function setUser(user: User): void {
    localStorage.setItem("arc_user", JSON.stringify(user));
}

export function getUser(): User | null {
    if (typeof window === "undefined") return null;
    const raw = localStorage.getItem("arc_user");
    if (!raw) return null;
    try { return JSON.parse(raw); } catch { return null; }
}

export function isAuthenticated(): boolean {
    return !!getAccessToken();
}
