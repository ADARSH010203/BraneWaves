/* ─── ARC Platform — useAuth Hook ─────────────────────────────────── */
"use client";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import type { User } from "@/types";
import { api } from "@/lib/api";
import { clearTokens, getUser, isAuthenticated, setTokens, setUser } from "@/lib/auth";

export function useAuth() {
    const [user, setCurrentUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);
    const router = useRouter();

    useEffect(() => {
        setCurrentUser(getUser());
        setLoading(false);
    }, []);

    const login = useCallback(async (email: string, password: string) => {
        const data = await api.login(email, password);
        setTokens(data.tokens.access_token, data.tokens.refresh_token);
        setUser(data.user);
        setCurrentUser(data.user);
        router.push("/dashboard");
    }, [router]);

    const register = useCallback(async (email: string, password: string, name: string) => {
        const data = await api.register(email, password, name);
        setTokens(data.tokens.access_token, data.tokens.refresh_token);
        setUser(data.user);
        setCurrentUser(data.user);
        router.push("/dashboard");
    }, [router]);

    const logout = useCallback(() => {
        clearTokens();
        setCurrentUser(null);
        router.push("/");
    }, [router]);

    return { user, loading, login, register, logout, isAuthenticated: isAuthenticated() };
}
