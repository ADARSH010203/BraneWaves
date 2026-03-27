/* ─── ARC Platform — Premium Dashboard Page ───────────────────────────────── */
"use client";
import { useEffect } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { useTask } from "@/hooks/useTask";
import { formatDate, getStatusColor, truncate } from "@/lib/utils";
import { PlusCircle, ClipboardList, Cpu, DollarSign, ArrowRight, Activity, Sparkles } from "lucide-react";

export default function DashboardPage() {
    const { tasks, total, loading, fetchTasks } = useTask();

    useEffect(() => { fetchTasks(); }, [fetchTasks]);

    const stats = [
        { label: "Total Tasks", value: total, icon: ClipboardList, color: "text-brand-400", bg: "bg-brand-500/10", border: "border-brand-500/20" },
        { label: "Active Agents", value: tasks.filter((t) => t.status === "running" || t.status === "planning").length * 7, icon: Cpu, color: "text-sky-400", bg: "bg-sky-500/10", border: "border-sky-500/20" },
        { label: "Completed", value: tasks.filter((t) => t.status === "completed").length, icon: CheckCircleIcon, color: "text-emerald-400", bg: "bg-emerald-500/10", border: "border-emerald-500/20" },
        { label: "Total Spent", value: `$${tasks.reduce((s, t) => s + (t.budget?.spent_usd || 0), 0).toFixed(2)}`, icon: DollarSign, color: "text-amber-400", bg: "bg-amber-500/10", border: "border-amber-500/20" },
    ];

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

            {/* ── Premium Task List ──────────────────────────────────────────────── */}
            <div className="glass-card overflow-hidden relative z-10">
                <div className="px-6 py-5 border-b border-white/10 flex items-center justify-between bg-slate-900/50 backdrop-blur-sm">
                    <div className="flex items-center gap-3">
                        <Activity className="h-5 w-5 text-brand-400" />
                        <h2 className="text-lg font-bold text-white">Recent Deployments</h2>
                    </div>
                </div>

                {loading ? (
                    <div className="p-20 text-center">
                        <div className="h-10 w-10 border-4 border-brand-500/20 border-t-brand-500 rounded-full animate-spin mx-auto mb-4 shadow-[0_0_15px_rgba(99,102,241,0.5)]" />
                        <p className="text-slate-400 font-medium animate-pulse">Synchronizing agent states...</p>
                    </div>
                ) : tasks.length === 0 ? (
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
                        {tasks.map((task, i) => (
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
