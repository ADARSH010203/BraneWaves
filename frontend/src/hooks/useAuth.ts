/* ─── ARC Platform — authoritative authentication hook ────────────── */
"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import type { User } from "@/types";
import { api } from "@/lib/api";
import { clearTokens, setTokens, setUser } from "@/lib/auth";

export function useAuth() {
    const [user, setCurrentUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);
    const router = useRouter();

    const refreshUser = useCallback(async () => {
        try {
            const authoritative = await api.getMe();
            setUser(authoritative);
            setCurrentUser(authoritative);
            return authoritative;
        } catch {
            clearTokens();
            setCurrentUser(null);
            return null;
        }
    }, []);

    useEffect(() => {
        let active = true;
        const bootstrap = async () => {
            try {
                const authoritative = await api.getMe();
                if (!active) return;
                setUser(authoritative);
                setCurrentUser(authoritative);
            } catch {
                if (!active) return;
                clearTokens();
                setCurrentUser(null);
            } finally {
                if (active) setLoading(false);
            }
        };

        const syncUser = (event: Event) => {
            const detail = (event as CustomEvent<User>).detail;
            if (detail) setCurrentUser(detail);
        };

        window.addEventListener("arc-user-updated", syncUser);
        void bootstrap();
        return () => {
            active = false;
            window.removeEventListener("arc-user-updated", syncUser);
        };
    }, []);

    const login = useCallback(async (email: string, password: string) => {
        const data = await api.login(email, password);
        setTokens(data.tokens.access_token);
        setUser(data.user);
        setCurrentUser(data.user);
        router.push("/dashboard");
    }, [router]);

    const register = useCallback(async (email: string, password: string, name: string) => {
        const data = await api.register(email, password, name);
        setTokens(data.tokens.access_token);
        setUser(data.user);
        setCurrentUser(data.user);
        router.push("/dashboard");
    }, [router]);

    const updateProfile = useCallback(async (name: string) => {
        const updated = await api.updateMe(name);
        setUser(updated);
        setCurrentUser(updated);
        return updated;
    }, []);

    const deleteAccount = useCallback(async () => {
        await api.deleteMe();
        clearTokens();
        setCurrentUser(null);
        router.push("/");
    }, [router]);

    const logout = useCallback(async () => {
        await api.logout();
        clearTokens();
        setCurrentUser(null);
        router.push("/");
    }, [router]);

    return {
        user,
        loading,
        login,
        register,
        logout,
        refreshUser,
        updateProfile,
        deleteAccount,
        isAuthenticated: !!user,
    };
}
