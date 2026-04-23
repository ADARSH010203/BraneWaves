/* ─── ARC Platform — Dashboard Layout ─────────────────────────────── */
"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import {
    Sparkles, LayoutDashboard, PlusCircle, BarChart3,
    Settings, LogOut, ChevronRight, Brain,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { CommandPalette } from "@/components/CommandPalette";

const navItems = [
    { href: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
    { href: "/dashboard/new", icon: PlusCircle, label: "New Task" },
    { href: "/dashboard/brain", icon: Brain, label: "ARC Brain" },
    { href: "/dashboard/knowledge-base", icon: Sparkles, label: "Knowledge Base" },
    { href: "/dashboard/costs", icon: BarChart3, label: "Cost Dashboard" },
    { href: "/dashboard/settings", icon: Settings, label: "Settings" },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();
    const router = useRouter();
    const { user, loading, isAuthenticated, logout } = useAuth();
    const [collapsed, setCollapsed] = useState(false);

    // Load collapsed state
    useEffect(() => {
        const saved = localStorage.getItem("arc_sidebar_collapsed");
        if (saved === "true") setCollapsed(true);
    }, []);

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
            <aside className={cn("shrink-0 bg-slate-900/40 backdrop-blur-2xl border-r border-white/5 flex flex-col relative z-20 shadow-[4px_0_24px_rgba(0,0,0,0.2)]", collapsed ? "w-[64px]" : "w-[280px]", "transition-all duration-300")} role="navigation" aria-label="Main navigation">
                <div className={`p-6 flex items-center gap-2 border-b border-white/5 ${collapsed ? "justify-center px-0" : ""}`}>
                    <Sparkles className="h-6 w-6 text-brand-500 shrink-0" />
                    {!collapsed && <span className="text-lg font-bold text-gradient">ARC</span>}
                </div>

                <nav className="flex-1 p-4 space-y-1">
                    {navItems.map((item) => {
                        const active = pathname === item.href || (item.href !== "/dashboard" && pathname?.startsWith(item.href));
                        return (
                            <Link key={item.href} href={item.href} title={collapsed ? item.label : undefined}
                                className={cn(
                                    "flex items-center rounded-xl text-sm font-medium transition-all duration-300 group relative overflow-hidden",
                                    collapsed ? "justify-center p-3" : "gap-3 px-4 py-3.5",
                                    active
                                        ? "text-white shadow-[0_4px_20px_rgba(99,102,241,0.15)]"
                                        : "text-slate-400 hover:text-white hover:bg-white/[0.03]"
                                )}>
                                {/* Active State Background */}
                                {active && <div className="absolute inset-0 bg-gradient-to-r from-brand-500/20 to-purple-500/10 border border-brand-500/30 rounded-xl" />}
                                
                                <item.icon className={cn("relative z-10 transition-transform duration-300 shrink-0", active ? "text-brand-400" : "group-hover:scale-110", collapsed ? "h-6 w-6" : "h-5 w-5")} />
                                {!collapsed && <span className="relative z-10 whitespace-nowrap">{item.label}</span>}
                                {active && !collapsed && <ChevronRight className="h-4 w-4 ml-auto relative z-10 text-brand-400/70" />}
                            </Link>
                        );
                    })}
                </nav>

                <div className="mt-auto">
                    {/* Command Palette Hint */}
                    {!collapsed && (
                        <div className="text-[10px] text-slate-500/70 mb-3 px-6 font-mono text-center">
                            Press <kbd className="px-1.5 py-0.5 rounded bg-white/5 border border-white/10 text-slate-400 font-sans">Cmd+K</kbd> to search
                        </div>
                    )}

                    {/* Toggle Button */}
                    <button
                        onClick={() => {
                            const next = !collapsed;
                            setCollapsed(next);
                            localStorage.setItem("arc_sidebar_collapsed", String(next));
                        }}
                        className="flex items-center justify-center mx-4 mb-2 p-2 rounded-xl text-slate-500 hover:text-white hover:bg-white/5 transition w-auto"
                        title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
                    >
                        <ChevronRight className={cn("h-4 w-4 transition-transform duration-300", collapsed ? "" : "rotate-180")} />
                    </button>

                    <div className="p-4 border-t border-white/5">
                        <div className={`flex items-center gap-3 ${collapsed ? "justify-center px-0 mb-4" : "px-4 py-3"}`}>
                            <div className="w-8 h-8 rounded-full bg-brand-500/20 flex items-center justify-center text-xs font-bold text-brand-400 shrink-0">
                                {user?.name?.[0]?.toUpperCase() || "U"}
                            </div>
                            {!collapsed && (
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm font-medium truncate">{user?.name || "User"}</p>
                                    <p className="text-xs text-slate-500 truncate">{user?.email}</p>
                                </div>
                            )}
                        </div>
                        <button onClick={logout}
                            className={cn(
                                "flex items-center rounded-xl text-sm text-slate-400 hover:text-red-400 hover:bg-red-500/5 transition",
                                collapsed ? "justify-center p-3 w-full" : "gap-2 px-4 py-2 mt-2 w-full"
                            )}
                            title={collapsed ? "Sign out" : undefined}
                            aria-label="Sign out">
                            <LogOut className={cn("shrink-0", collapsed ? "h-5 w-5" : "h-4 w-4")} /> {!collapsed && "Sign Out"}
                        </button>
                    </div>
                </div>
            </aside>

            {/* ── Main Content ────────────────────────────────────────────── */}
            <main className="flex-1 overflow-auto relative z-10 custom-scrollbar">
                <div className="p-8 max-w-[1400px] mx-auto min-h-full">{children}</div>
            </main>

            <CommandPalette />
        </div>
    );
}
