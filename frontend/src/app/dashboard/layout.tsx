/* ─── ARC Platform — Dashboard Layout ─────────────────────────────── */
"use client";
import { useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import {
    Sparkles, LayoutDashboard, PlusCircle, BarChart3,
    Settings, LogOut, ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
    { href: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
    { href: "/dashboard/new", icon: PlusCircle, label: "New Task" },
    { href: "/dashboard/costs", icon: BarChart3, label: "Cost Dashboard" },
    { href: "/dashboard/settings", icon: Settings, label: "Settings" },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();
    const router = useRouter();
    const { user, loading, isAuthenticated, logout } = useAuth();

    // Auth guard — redirect to login if not authenticated
    useEffect(() => {
        if (!loading && !isAuthenticated) {
            router.push("/login");
        }
    }, [loading, isAuthenticated, router]);

    // Show loading state while checking auth
    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="h-8 w-8 border-2 border-brand-500/30 border-t-brand-500 rounded-full animate-spin" />
            </div>
        );
    }

    // Don't render dashboard if not authenticated
    if (!isAuthenticated) {
        return null;
    }

    return (
        <div className="min-h-screen flex bg-surface-900 overflow-hidden relative">
            {/* ── Background Grid ── */}
            <div className="absolute inset-0 z-0 pointer-events-none">
                <div className="absolute inset-0 bg-grid-white opacity-[0.03]" />
                <div className="absolute top-0 right-0 w-[50%] h-[50%] bg-brand-500/5 rounded-full blur-[120px] mix-blend-screen" />
            </div>

            {/* ── Sidebar ────────────────────────────────────────────────── */}
            <aside className="w-[280px] shrink-0 bg-slate-900/40 backdrop-blur-2xl border-r border-white/5 flex flex-col relative z-20 shadow-[4px_0_24px_rgba(0,0,0,0.2)]" role="navigation" aria-label="Main navigation">
                <div className="p-6 flex items-center gap-2 border-b border-white/5">
                    <Sparkles className="h-6 w-6 text-brand-500" />
                    <span className="text-lg font-bold text-gradient">ARC</span>
                </div>

                <nav className="flex-1 p-4 space-y-1">
                    {navItems.map((item) => {
                        const active = pathname === item.href || (item.href !== "/dashboard" && pathname?.startsWith(item.href));
                        return (
                            <Link key={item.href} href={item.href}
                                className={cn(
                                    "flex items-center gap-3 px-4 py-3.5 rounded-xl text-sm font-medium transition-all duration-300 group relative overflow-hidden",
                                    active
                                        ? "text-white shadow-[0_4px_20px_rgba(99,102,241,0.15)]"
                                        : "text-slate-400 hover:text-white hover:bg-white/[0.03]"
                                )}>
                                {/* Active State Background */}
                                {active && <div className="absolute inset-0 bg-gradient-to-r from-brand-500/20 to-purple-500/10 border border-brand-500/30 rounded-xl" />}
                                
                                <item.icon className={cn("h-5 w-5 relative z-10 transition-transform duration-300", active ? "text-brand-400" : "group-hover:scale-110")} />
                                <span className="relative z-10">{item.label}</span>
                                {active && <ChevronRight className="h-4 w-4 ml-auto relative z-10 text-brand-400/70" />}
                            </Link>
                        );
                    })}
                </nav>

                <div className="p-4 border-t border-white/5">
                    <div className="flex items-center gap-3 px-4 py-3">
                        <div className="w-8 h-8 rounded-full bg-brand-500/20 flex items-center justify-center text-xs font-bold text-brand-400">
                            {user?.name?.[0]?.toUpperCase() || "U"}
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium truncate">{user?.name || "User"}</p>
                            <p className="text-xs text-slate-500 truncate">{user?.email}</p>
                        </div>
                    </div>
                    <button onClick={logout}
                        className="flex items-center gap-2 px-4 py-2 mt-2 w-full rounded-xl text-sm text-slate-400 hover:text-red-400 hover:bg-red-500/5 transition"
                        aria-label="Sign out">
                        <LogOut className="h-4 w-4" /> Sign Out
                    </button>
                </div>
            </aside>

            {/* ── Main Content ────────────────────────────────────────────── */}
            <main className="flex-1 overflow-auto relative z-10 custom-scrollbar">
                <div className="p-8 max-w-[1400px] mx-auto min-h-full">{children}</div>
            </main>
        </div>
    );
}
