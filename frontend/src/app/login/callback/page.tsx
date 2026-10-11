"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { clearTokens, setTokens, setUser } from "@/lib/auth";

export default function AuthCallbackPage() {
    const router = useRouter();

    useEffect(() => {
        let active = true;

        const finishOAuth = async () => {
            const hash = window.location.hash.substring(1);
            const params = new URLSearchParams(hash);
            const accessToken = params.get("access_token");

            // Remove the access-token fragment from browser history immediately.
            window.history.replaceState({}, document.title, window.location.pathname);

            if (!accessToken) {
                router.replace("/login?error=oauth_failed");
                return;
            }

            try {
                setTokens(accessToken);
                const user = await api.getMe();
                if (!active) return;
                setUser(user);
                router.replace("/dashboard");
            } catch {
                clearTokens();
                if (active) router.replace("/login?error=oauth_failed");
            }
        };

        void finishOAuth();
        return () => { active = false; };
    }, [router]);

    return (
        <div className="min-h-screen flex items-center justify-center bg-surface-900 overflow-hidden relative">
            <div className="absolute inset-0 z-0 pointer-events-none">
                <div className="absolute inset-0 bg-grid-white opacity-[0.02]" />
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[50%] h-[50%] bg-brand-500/10 rounded-full blur-[120px] mix-blend-screen" />
            </div>
            <div className="relative z-10 flex flex-col items-center gap-6">
                <div className="relative">
                    <div className="absolute inset-0 border-4 border-brand-500/20 border-t-brand-500 rounded-full animate-spin" />
                    <div className="p-4 bg-slate-900/80 rounded-full">
                        <Sparkles className="h-8 w-8 text-brand-400" />
                    </div>
                </div>
                <div className="text-center">
                    <h2 className="text-xl font-bold text-white mb-2">Authenticating</h2>
                    <p className="text-sm font-mono text-brand-300">Loading your verified account…</p>
                </div>
            </div>
        </div>
    );
}
