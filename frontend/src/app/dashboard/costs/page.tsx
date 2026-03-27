/* ─── ARC Platform — Premium Cost Dashboard ───────────────────────────────── */
"use client";
import { useEffect } from "react";
import { motion } from "framer-motion";
import { useTask } from "@/hooks/useTask";
import { formatCost } from "@/lib/utils";
import { BarChart3, DollarSign, Cpu, TrendingUp, Sparkles, Wallet } from "lucide-react";

export default function CostDashboard() {
  const { tasks, fetchTasks } = useTask();
  useEffect(() => { fetchTasks(); }, [fetchTasks]);

  const totalCost = tasks.reduce((s, t) => s + (t.budget?.spent_usd || 0), 0);
  const totalBudget = tasks.reduce((s, t) => s + (t.budget?.max_usd || 0), 0);
  const totalSteps = tasks.reduce((s, t) => s + (t.budget?.steps_used || 0), 0);
  const utilization = totalBudget > 0 ? (totalCost / totalBudget) * 100 : 0;

  const stats = [
    { icon: DollarSign, label: "Total Spent", value: formatCost(totalCost), color: "text-amber-400", bg: "bg-amber-500/10", border: "border-amber-500/20" },
    { icon: TrendingUp, label: "Total Budget", value: formatCost(totalBudget), color: "text-emerald-400", bg: "bg-emerald-500/10", border: "border-emerald-500/20" },
    { icon: BarChart3, label: "Tasks Run", value: tasks.length, color: "text-brand-400", bg: "bg-brand-500/10", border: "border-brand-500/20" },
    { icon: Cpu, label: "Agent Steps", value: totalSteps, color: "text-sky-400", bg: "bg-sky-500/10", border: "border-sky-500/20" },
  ];

  return (
    <div className="animate-fade-in">
      <div className="flex items-center gap-3 mb-2">
        <Wallet className="h-6 w-6 text-brand-400" />
        <h1 className="text-3xl md:text-4xl font-black text-white tracking-tight">Cost Analytics</h1>
      </div>
      <p className="text-slate-400 text-lg mb-10">Track token spending and budget utilization across all deployments.</p>

      {/* Premium Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6 mb-10">
        {stats.map((s, i) => (
          <motion.div key={s.label} initial={{opacity:0, y:20}} animate={{opacity:1, y:0}}
            transition={{delay: i * 0.1, duration: 0.5}}
            className={`glass-card p-6 border ${s.border} relative overflow-hidden group`}>
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

      {/* Budget Utilization Bar */}
      <motion.div initial={{opacity:0, y:20}} animate={{opacity:1, y:0}} transition={{delay:0.4}}
        className="glass-card p-6 mb-10">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-bold text-white flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-emerald-400" /> Overall Budget Utilization
          </h2>
          <span className="text-2xl font-black text-white">{utilization.toFixed(1)}%</span>
        </div>
        <div className="h-4 rounded-full bg-slate-800 overflow-hidden">
          <motion.div initial={{width:0}} animate={{width: `${Math.min(100, utilization)}%`}}
            transition={{duration:1.5, ease:"easeOut"}}
            className={`h-full rounded-full ${
              utilization > 80 ? "bg-gradient-to-r from-red-500 to-orange-500" :
              utilization > 50 ? "bg-gradient-to-r from-amber-500 to-yellow-500" :
              "bg-gradient-to-r from-emerald-500 to-cyan-500"
            }`} />
        </div>
        <div className="flex justify-between text-xs text-slate-500 mt-2">
          <span>$0.00</span><span>{formatCost(totalBudget)}</span>
        </div>
      </motion.div>

      {/* Per-Task Breakdown */}
      <div className="glass-card overflow-hidden">
        <div className="px-6 py-5 border-b border-white/10 bg-slate-900/50 flex items-center gap-3">
          <BarChart3 className="h-5 w-5 text-brand-400" />
          <h2 className="font-bold text-white">Per-Task Cost Breakdown</h2>
        </div>

        {tasks.length === 0 ? (
          <div className="p-16 text-center">
            <Sparkles className="h-12 w-12 text-slate-600 mx-auto mb-4" />
            <h3 className="text-lg font-bold text-white mb-2">No cost data yet</h3>
            <p className="text-slate-400">Create and run tasks to see spending analytics here.</p>
          </div>
        ) : (
          <div className="divide-y divide-white/5">
            {tasks.map((task, i) => {
              const spent = task.budget?.spent_usd || 0;
              const max = task.budget?.max_usd || 1;
              const pct = (spent / max) * 100;
              return (
                <motion.div key={task.id} initial={{opacity:0}} animate={{opacity:1}} transition={{delay: i * 0.05}}
                  className="px-6 py-5 flex items-center gap-6 hover:bg-slate-800/30 transition-colors">
                  <div className="flex-1 min-w-0">
                    <p className="font-bold text-sm text-slate-200 truncate">{task.title}</p>
                    <p className="text-xs text-slate-500 mt-0.5 capitalize">{task.status}</p>
                  </div>
                  <div className="text-right shrink-0 w-24">
                    <p className="text-sm font-black text-white">{formatCost(spent)}</p>
                    <p className="text-xs text-slate-500">of {formatCost(max)}</p>
                  </div>
                  <div className="w-32 shrink-0">
                    <div className="h-2.5 rounded-full bg-slate-800 overflow-hidden">
                      <div className={`h-full rounded-full transition-all duration-700 ${
                        pct > 80 ? "bg-gradient-to-r from-red-500 to-orange-500" :
                        pct > 50 ? "bg-gradient-to-r from-amber-500 to-yellow-400" :
                        "bg-gradient-to-r from-brand-500 to-cyan-500"
                      }`} style={{ width: `${Math.min(100, pct)}%` }} />
                    </div>
                    <p className="text-[10px] text-slate-500 text-right mt-1">{pct.toFixed(0)}%</p>
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
