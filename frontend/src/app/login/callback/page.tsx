"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Sparkles } from "lucide-react";

export default function AuthCallbackPage() {
    const router = useRouter();

    useEffect(() => {
        // Parse the hash parameters inserted by the backend redirect
        const hash = window.location.hash.substring(1);
        const params = new URLSearchParams(hash);
        
        const accessToken = params.get("access_token");
        const refreshToken = params.get("refresh_token");

        if (accessToken && refreshToken) {
            localStorage.setItem("arc_access_token", accessToken);
            localStorage.setItem("arc_refresh_token", refreshToken);
            // Simulate brief loading state to ensure context switches cleanly
            setTimeout(() => {
                router.push("/dashboard");
            }, 1000);
        } else {
            router.push("/login?error=oauth_failed");
        }
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
                    <p className="text-sm font-mono text-brand-300 flex items-center gap-2">
                        Verifying OAuth provider credentials<span className="animate-pulse">...</span>
                    </p>
                </div>
            </div>
        </div>
    );
}
