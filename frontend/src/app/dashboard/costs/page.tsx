"use client";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { 
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, 
  PieChart, Pie, Cell, AreaChart, Area, CartesianGrid, Legend 
} from "recharts";
import { api } from "@/lib/api";
import { Activity, DollarSign, Cpu, History } from "lucide-react";
import { DashboardSkeleton } from "@/components/skeletons/DashboardSkeleton";
import { formatCost } from "@/lib/utils";

export default function CostsDashboardPage() {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const response = await api.getCostAnalytics();
        setData(response.data);
      } catch (err) {
        console.error("Failed to load analytics:", err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) return <DashboardSkeleton />;

  if (!data) return (
    <div className="flex flex-col items-center justify-center py-32 text-center">
      <Activity className="h-12 w-12 text-slate-600 mb-4" />
      <h2 className="text-xl font-bold text-white mb-2">No Data Available</h2>
      <p className="text-slate-400">Run some agents to generate cost analytics.</p>
    </div>
  );

  const stats = [
    { label: "Total Spent", value: formatCost(data.total_spent_usd), icon: DollarSign, color: "text-amber-400", bg: "bg-amber-500/10" },
    { label: "Avg Per Task", value: formatCost(data.tasks_comparison?.length ? data.total_spent_usd / data.tasks_comparison.length : 0), icon: Activity, color: "text-brand-400", bg: "bg-brand-500/10" },
    { label: "Active Models", value: data.agent_breakdown?.length || 0, icon: Cpu, color: "text-sky-400", bg: "bg-sky-500/10" },
    { label: "Total Runs", value: data.agent_breakdown?.reduce((sum: number, a: any) => sum + a.runs, 0) || 0, icon: History, color: "text-purple-400", bg: "bg-purple-500/10" },
  ];

  const pieColors = ["#3b82f6", "#10b981", "#8b5cf6", "#f43f5e", "#f59e0b", "#06b6d4"];

  return (
    <div className="animate-fade-in relative z-10 w-full max-w-7xl mx-auto">
      <div className="mb-10">
        <h1 className="text-3xl md:text-4xl font-bold tracking-tight text-white mb-2 flex items-center gap-3">
          Cost Analytics <DollarSign className="h-6 w-6 text-brand-400" />
        </h1>
        <p className="text-slate-400">Analyze LLM token usage and spending patterns across all agents.</p>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6 mb-10">
        {stats.map((s, i) => (
          <motion.div key={s.label} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }}
            className="glass-card p-6 border border-white/5 relative overflow-hidden group">
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

      <div className="grid lg:grid-cols-2 gap-8 mb-8">
        {/* Daily Trend */}
        <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.2 }}
          className="glass-card p-6 border border-white/5">
          <h3 className="text-lg font-bold text-white mb-6 flex items-center gap-2">
            <Activity className="h-5 w-5 text-brand-400" /> Daily Spending Trend (Last 30 Days)
          </h3>
          <div className="h-[300px]">
             <ResponsiveContainer width="100%" height="100%">
               <AreaChart data={data.daily_trend}>
                 <defs>
                   <linearGradient id="colorCost" x1="0" y1="0" x2="0" y2="1">
                     <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3}/>
                     <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                   </linearGradient>
                 </defs>
                 <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                 <XAxis dataKey="date" stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} tickFormatter={(str) => str.split("-").slice(1).join("/")} />
                 <YAxis stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} tickFormatter={(val) => `$${val}`} />
                 <Tooltip 
                   contentStyle={{ backgroundColor: "#0f172a", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px" }}
                   itemStyle={{ color: "#e2e8f0" }}
                   formatter={(val: number) => [`$${val.toFixed(4)}`, "Cost"]}
                 />
                 <Area type="monotone" dataKey="cost" stroke="#6366f1" strokeWidth={3} fillOpacity={1} fill="url(#colorCost)" />
               </AreaChart>
             </ResponsiveContainer>
          </div>
        </motion.div>

        {/* Agent Breakdown */}
        <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.3 }}
          className="glass-card p-6 border border-white/5">
          <h3 className="text-lg font-bold text-white mb-6 flex items-center gap-2">
            <PieChart className="h-5 w-5 text-purple-400" /> Cost By Agent Type
          </h3>
          <div className="h-[300px] flex items-center justify-center">
             {data.agent_breakdown?.length > 0 ? (
               <ResponsiveContainer width="100%" height="100%">
                 <PieChart>
                   <Pie
                     data={data.agent_breakdown}
                     cx="50%"
                     cy="50%"
                     innerRadius={80}
                     outerRadius={110}
                     paddingAngle={5}
                     dataKey="value"
                   >
                     {data.agent_breakdown.map((_: any, index: number) => (
                       <Cell key={`cell-${index}`} fill={pieColors[index % pieColors.length]} />
                     ))}
                   </Pie>
                   <Tooltip 
                     contentStyle={{ backgroundColor: "#0f172a", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px" }}
                     formatter={(val: number) => [`$${val.toFixed(4)}`, "Total Cost"]}
                   />
                   <Legend verticalAlign="bottom" height={36} />
                 </PieChart>
               </ResponsiveContainer>
             ) : (
               <p className="text-slate-500">No agent data available</p>
             )}
          </div>
        </motion.div>
      </div>

      {/* Task Comparison Bar Chart */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}
        className="glass-card p-6 border border-white/5">
        <h3 className="text-lg font-bold text-white mb-6 flex items-center gap-2">
          <History className="h-5 w-5 text-sky-400" /> Recent Workflow Costs
        </h3>
        <div className="h-[350px]">
           <ResponsiveContainer width="100%" height="100%">
             <BarChart data={data.tasks_comparison} layout="vertical" margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
               <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={true} vertical={false} />
               <XAxis type="number" stroke="#64748b" tickFormatter={(val) => `$${val}`} />
               <YAxis dataKey="task" type="category" width={150} stroke="#cbd5e1" fontSize={12} tickLine={false} axisLine={false} />
               <Tooltip 
                 cursor={{ fill: 'rgba(255,255,255,0.02)' }}
                 contentStyle={{ backgroundColor: "#0f172a", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px" }}
                 formatter={(val: number) => [`$${val.toFixed(4)}`, "Cost"]}
               />
               <Bar dataKey="cost" fill="#3b82f6" radius={[0, 4, 4, 0]}>
                 {data.tasks_comparison?.map((entry: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={entry.status === 'completed' ? '#10b981' : entry.status === 'failed' ? '#ef4444' : '#3b82f6'} />
                 ))}
               </Bar>
             </BarChart>
           </ResponsiveContainer>
        </div>
      </motion.div>
    </div>
  );
}
