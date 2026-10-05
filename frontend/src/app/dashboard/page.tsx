/* ─── ARC Platform — Premium Dashboard Page ───────────────────────────────── */
"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { useTask } from "@/hooks/useTask";
import { formatDate, getStatusColor, truncate, cn } from "@/lib/utils";
import { PlusCircle, ClipboardList, Cpu, DollarSign, ArrowRight, Activity, Sparkles } from "lucide-react";
import { DashboardSkeleton } from "@/components/skeletons/DashboardSkeleton";

export default function DashboardPage() {
    const { tasks, total, loading, fetchTasks } = useTask();
    const [statusFilter, setStatusFilter] = useState<string>("all");

    useEffect(() => { fetchTasks(); }, [fetchTasks]);

    if (loading && tasks.length === 0) {
        return <DashboardSkeleton />;
    }

    const stats = [
        { label: "Total Tasks", value: total, icon: ClipboardList, color: "text-brand-400", bg: "bg-brand-500/10", border: "border-brand-500/20" },
        { label: "Active Agents", value: tasks.filter((t) => t.status === "running" || t.status === "planning").length * 7, icon: Cpu, color: "text-sky-400", bg: "bg-sky-500/10", border: "border-sky-500/20" },
        { label: "Completed", value: tasks.filter((t) => t.status === "completed").length, icon: CheckCircleIcon, color: "text-emerald-400", bg: "bg-emerald-500/10", border: "border-emerald-500/20" },
        { label: "Total Spent", value: `$${tasks.reduce((s, t) => s + (t.budget?.spent_usd || 0), 0).toFixed(2)}`, icon: DollarSign, color: "text-amber-400", bg: "bg-amber-500/10", border: "border-amber-500/20" },
    ];

    const filteredTasks = statusFilter === "all" ? tasks : tasks.filter(t => t.status === statusFilter);

    return (
        <div className="animate-fade-in relative">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-10 gap-4 relative z-10">
                <div>
                    <h1 className="text-3xl md:text-4xl font-bold tracking-tight text-white mb-2 flex items-center gap-3">
                        Dashboard Overview <Sparkles className="h-6 w-6 text-brand-400 animate-pulse" />
                    </h1>
                    <p className="text-slate-400">Monitor your active AI research agents and token usage.</p>
                </div>
                <Link href="/dashboard/new" className="btn-brand flex items-center gap-2 shadow-[0_0_20px_rgba(99,102,241,0.3)]">
                    <PlusCircle className="h-5 w-5" /> Deploy New Tasks
                </Link>
            </div>

            {/* ── Premium Animated Stats ──────────────────────────────────────────────────── */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6 mb-10 relative z-10">
                {stats.map((s, i) => (
                    <motion.div key={s.label} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.1, duration: 0.5, ease: "easeOut" }} 
                        className={`glass-card p-6 border ${s.border} relative overflow-hidden group`}>
                        {/* Hover Gradient Effect */}
                        <div className="absolute inset-0 bg-gradient-to-br from-white/[0.02] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                        
                        <div className="flex flex-col gap-4 relative z-10">
                            <div className={`w-12 h-12 rounded-xl ${s.bg} flex items-center justify-center`}>
                                <s.icon className={`h-6 w-6 ${s.color}`} />
                            </div>
                            <div>
                                <h3 className="text-3xl font-black text-white tracking-tight">{s.value}</h3>
                                <p className="text-sm font-medium text-slate-400 mt-1">{s.label}</p>
                            </div>
                        </div>
                    </motion.div>
                ))}
            </div>

            {/* ── 2-Column Dashboard Layout ────────────────────────────────────────────── */}
            <div className="flex flex-col lg:flex-row gap-6 relative z-10">
                <div className="flex-1 min-w-0">
                    {/* ── Premium Task List ──────────────────────────────────────────────── */}
                    <div className="glass-card overflow-hidden relative z-10">
                        <div className="px-6 py-5 border-b border-white/10 flex items-center justify-between bg-slate-900/50 backdrop-blur-sm">
                            <div className="flex items-center gap-3">
                                <Activity className="h-5 w-5 text-brand-400" />
                                <h2 className="text-lg font-bold text-white">Recent Deployments</h2>
                            </div>
                        </div>

                        {/* Filter Tabs */}
                        <div className="flex gap-1 px-6 py-3 border-b border-white/5 overflow-x-auto">
                            {[
                                { label: "All", value: "all" },
                                { label: "Running", value: "running" },
                                { label: "Completed", value: "completed" },
                                { label: "Failed", value: "failed" },
                            ].map(f => (
                                <button
                                    key={f.value}
                                    onClick={() => setStatusFilter(f.value)}
                                    className={cn(
                                        "px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition",
                                        statusFilter === f.value
                                            ? "bg-brand-500/20 text-brand-300"
                                            : "text-slate-400 hover:text-white"
                                    )}
                                >
                                    {f.label}
                                    <span className="ml-1.5 text-[10px] text-slate-500">
                                        {f.value === "all" ? tasks.length : tasks.filter(t => t.status === f.value).length}
                                    </span>
                                </button>
                            ))}
                        </div>

                        {loading ? (
                            <div className="p-20 text-center">
                                <div className="h-10 w-10 border-4 border-brand-500/20 border-t-brand-500 rounded-full animate-spin mx-auto mb-4 shadow-[0_0_15px_rgba(99,102,241,0.5)]" />
                                <p className="text-slate-400 font-medium animate-pulse">Synchronizing agent states...</p>
                            </div>
                        ) : filteredTasks.length === 0 ? (
                    <div className="p-20 text-center relative overflow-hidden">
                        <div className="absolute inset-0 bg-gradient-to-b from-transparent to-brand-500/5" />
                        <ClipboardList className="h-16 w-16 text-slate-600 mx-auto mb-4 relative z-10" />
                        <h3 className="text-xl font-bold text-white mb-2 relative z-10">No active tasks</h3>
                        <p className="text-slate-400 max-w-sm mx-auto relative z-10 mb-6">
                            Deploy your first agentic workflow to see the multi-model pipeline in action.
                        </p>
                        <Link href="/dashboard/new" className="btn-brand inline-flex items-center gap-2 relative z-10">
                            <PlusCircle className="h-5 w-5" /> Initialize Workflow
                        </Link>
                    </div>
                    ) : (
                        <div className="divide-y divide-white/5">
                            {filteredTasks.map((task, i) => (
                            <motion.div key={task.id} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: i * 0.05 + 0.3, duration: 0.4 }}>
                                <Link href={`/dashboard/tasks/${task.id}`}
                                    className="flex items-center gap-4 px-6 py-5 hover:bg-slate-800/40 transition-colors group">
                                    <div className="flex-1 min-w-0">
                                        <h3 className="font-bold text-slate-200 group-hover:text-brand-300 transition-colors truncate text-base">
                                            {task.title}
                                        </h3>
                                        <p className="text-sm text-slate-500 mt-1 truncate">
                                            {truncate(task.description, 120)}
                                        </p>
                                    </div>
                                    <div className="text-right">
                                        <div className="mb-2 flex justify-end">
                                            <span className={getStatusColor(task.status)}>
                                                {task.status === "running" ? (
                                                    <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" /> {task.status}</span>
                                                ) : task.status}
                                            </span>
                                        </div>
                                        <span className="text-xs font-mono text-slate-500 hidden sm:block">
                                            {formatDate(task.created_at)}
                                        </span>
                                    </div>
                                    <ArrowRight className="h-5 w-5 text-slate-600 group-hover:text-brand-400 group-hover:translate-x-1 transition-all ml-4" />
                                </Link>
                            </motion.div>
                        ))}
                    </div>
                )}
                    </div>
                </div>

                {/* Right Panel: Live Activity */}
                <div className="hidden lg:block w-72 shrink-0 space-y-4">
                  {/* Quick Actions */}
                  <div className="glass-card p-4">
                    <h3 className="text-sm font-bold text-white mb-3">Quick Actions</h3>
                    <div className="space-y-2">
                      <Link href="/dashboard/new" className="flex items-center gap-2 w-full px-3 py-2.5 rounded-xl bg-brand-500/10 border border-brand-500/20 text-brand-300 text-sm hover:bg-brand-500/20 transition">
                        <PlusCircle className="h-4 w-4" /> New Task
                      </Link>
                      <Link href="/dashboard/knowledge-base" className="flex items-center gap-2 w-full px-3 py-2.5 rounded-xl bg-slate-800/50 border border-white/5 text-slate-300 text-sm hover:bg-slate-700/50 transition">
                        <Sparkles className="h-4 w-4" /> Upload Document
                      </Link>
                    </div>
                  </div>
                  {/* Live Agents */}
                  <div className="glass-card p-4">
                    <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
                      Live Agents
                    </h3>
                    {tasks.filter(t => t.status === "running" || t.status === "planning").length === 0 ? (
                      <p className="text-xs text-slate-500 text-center py-4">All agents idle</p>
                    ) : (
                      <div className="space-y-2">
                        {tasks.filter(t => t.status === "running" || t.status === "planning").map(task => (
                          <Link key={task.id} href={`/dashboard/tasks/${task.id}`}
                            className="block px-3 py-2 rounded-xl bg-blue-500/5 border border-blue-500/20 hover:bg-blue-500/10 transition">
                            <p className="text-xs font-medium text-blue-300 truncate">{task.title}</p>
                            <p className="text-[10px] text-slate-500 mt-0.5 capitalize">{task.status}...</p>
                          </Link>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
            </div>
        </div>
    );
}

// Simple internal icon for CheckCircle to avoid massive lucide imports if unnecessary
function CheckCircleIcon(props: any) {
    return (
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
            <polyline points="22 4 12 14.01 9 11.01" />
        </svg>
    )
}
