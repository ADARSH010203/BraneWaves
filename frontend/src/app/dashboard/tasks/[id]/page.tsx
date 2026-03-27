"use client";
import { useEffect } from "react";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useTask } from "@/hooks/useTask";
import { useWebSocket } from "@/hooks/useWebSocket";
import { formatDate, formatCost, getStatusColor, getAgentBadgeClass } from "@/lib/utils";
import { Activity, FileText, DollarSign, CheckCircle2, AlertTriangle, Clock, Wifi, Terminal } from "lucide-react";
import type { TaskStep, WSEvent } from "@/types";

export default function TaskDetailPage() {
  const params = useParams();
  const taskId = params?.id as string;
  const { currentTask, steps, result, fetchTask, fetchSteps, fetchResult, loading } = useTask();
  const { events, connected, latestEvent } = useWebSocket(
    currentTask?.status === "running" || currentTask?.status === "planning" ? taskId : null
  );

  useEffect(() => {
    if (taskId) { fetchTask(taskId); fetchSteps(taskId); }
  }, [taskId, fetchTask, fetchSteps]);

  useEffect(() => {
    if (currentTask?.status === "completed") fetchResult(taskId);
  }, [currentTask?.status, taskId, fetchResult]);

  // Refresh steps on WS events
  useEffect(() => {
    if (latestEvent) { fetchTask(taskId); fetchSteps(taskId); }
  }, [latestEvent, taskId, fetchTask, fetchSteps]);

  if (loading && !currentTask) return (
    <div className="flex items-center justify-center py-32">
      <div className="h-12 w-12 border-4 border-brand-500/20 border-t-brand-500 rounded-full animate-spin shadow-[0_0_20px_rgba(99,102,241,0.5)]" />
    </div>
  );

  if (!currentTask) return (
    <div className="flex flex-col items-center justify-center py-32 text-center">
      <AlertTriangle className="h-12 w-12 text-slate-600 mb-4" />
      <h2 className="text-xl font-bold text-white mb-2">Task Not Found</h2>
      <p className="text-slate-400">This task might have been deleted or the ID is invalid.</p>
    </div>
  );

  return (
    <div className="animate-fade-in relative z-10">
      {/* Header */}
      <div className="glass-card p-6 mb-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-l-4 border-l-brand-500">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-2xl md:text-3xl font-black text-white tracking-tight">{currentTask.title}</h1>
            <span className={`px-3 py-1 text-xs font-bold uppercase tracking-wider rounded-full backdrop-blur-md border ${
              currentTask.status === "running" ? "bg-blue-500/20 text-blue-400 border-blue-500/30 animate-pulse" :
              currentTask.status === "completed" ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" :
              currentTask.status === "failed" ? "bg-red-500/20 text-red-400 border-red-500/30" :
              "bg-amber-500/20 text-amber-400 border-amber-500/30"
            }`}>
              {currentTask.status}
            </span>
          </div>
          <p className="text-slate-400 text-sm md:text-base max-w-2xl leading-relaxed">{currentTask.description}</p>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <div className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium border transition-colors ${
            connected ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20 shadow-[0_0_15px_rgba(16,185,129,0.15)]" : "bg-slate-800/50 text-slate-400 border-slate-700"
          }`}>
            <Wifi className={`h-4 w-4 ${connected ? "animate-pulse" : ""}`} />
            {connected ? "Stream Live" : "Stream Offline"}
          </div>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {[
          { icon: Activity, label: "Execution Steps", value: `${steps.filter(s=>s.status==="completed").length} / ${steps.length}`, color: "text-brand-400", bg: "bg-brand-500/10" },
          { icon: Clock, label: "Launched At", value: formatDate(currentTask.created_at).split(",")[0], color: "text-sky-400", bg: "bg-sky-500/10" },
          { icon: DollarSign, label: "Total Cost", value: formatCost(currentTask.budget?.spent_usd||0), color: "text-amber-400", bg: "bg-amber-500/10" },
          { icon: CheckCircle2, label: "Budget Limit", value: formatCost(currentTask.budget?.max_usd||0), color: "text-emerald-400", bg: "bg-emerald-500/10" },
        ].map((s,i)=>(
          <motion.div key={s.label} initial={{opacity:0,y:10}} animate={{opacity:1,y:0}} transition={{delay:i*0.05}} 
            className="p-5 rounded-2xl bg-slate-800/40 border border-white/5 backdrop-blur-sm flex items-center gap-4 hover:bg-slate-800/60 transition-colors">
            <div className={`w-12 h-12 rounded-full ${s.bg} flex items-center justify-center shrink-0`}>
              <s.icon className={`h-6 w-6 ${s.color}`} />
            </div>
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">{s.label}</p>
              <p className="text-lg font-bold text-white tracking-tight">{s.value}</p>
            </div>
          </motion.div>
        ))}
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Agent Timeline UI */}
        <div className="lg:col-span-2 glass-card overflow-hidden flex flex-col h-[700px]">
          <div className="px-6 py-4 bg-slate-900/80 border-b border-white/10 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-brand-400"/>
              <h2 className="font-bold text-white tracking-tight">Agent DAG Execution Graph</h2>
            </div>
            <span className="text-xs text-slate-400 font-mono">v1.0.0</span>
          </div>
          <div className="flex-1 overflow-auto custom-scrollbar p-6">
            {steps.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-slate-500">
                <Activity className="h-10 w-10 mb-4 opacity-50" />
                <p className="font-medium animate-pulse">Waiting for DAG orchestrator...</p>
              </div>
            ) : (
              <div className="relative border-l-2 border-slate-700/50 ml-4 space-y-6 pb-4">
                {steps.map((step: TaskStep, i: number) => (
                  <motion.div key={step.id} initial={{opacity:0, x:-10}} animate={{opacity:1, x:0}} transition={{delay:i*0.05}}
                    className="relative pl-8">
                    {/* Timeline Node */}
                    <div className={`absolute -left-[11px] top-1.5 w-5 h-5 rounded-full border-4 border-slate-900 ${
                      step.status === "completed" ? "bg-emerald-500 shadow-[0_0_10px_#10b981]" :
                      step.status === "running" ? "bg-blue-500 animate-pulse shadow-[0_0_10px_#3b82f6]" :
                      step.status === "failed" ? "bg-red-500 shadow-[0_0_10px_#ef4444]" :
                      "bg-slate-600"
                    }`} />
                    
                    <div className="bg-slate-800/40 border border-white/5 rounded-xl p-4 hover:border-brand-500/30 transition-colors group">
                      <div className="flex flex-wrap items-center gap-3 mb-2">
                        <span className="text-xs font-mono text-slate-500 w-6">#{step.order}</span>
                        <span className={getAgentBadgeClass(step.agent_type)}>{step.agent_type} agent</span>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                          step.status === "completed" ? "bg-emerald-500/10 text-emerald-400" :
                          step.status === "running" ? "bg-blue-500/10 text-blue-400" :
                          step.status === "failed" ? "bg-red-500/10 text-red-400" :
                          "bg-slate-500/10 text-slate-400"
                        }`}>
                          {step.status}
                        </span>
                        {step.confidence != null && (
                          <span className="ml-auto text-xs font-mono text-brand-300 bg-brand-500/10 px-2 py-1 rounded">
                            Conf: {(step.confidence*100).toFixed(0)}%
                          </span>
                        )}
                      </div>
                      <h4 className="font-semibold text-slate-200 text-sm leading-relaxed">{step.title}</h4>
                      {step.error && (
                        <div className="mt-3 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-300 font-mono flex items-start gap-2">
                          <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5"/>
                          <span className="break-all">{step.error}</span>
                        </div>
                      )}
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Live Terminal UX */}
        <div className="rounded-2xl border border-emerald-500/20 shadow-[0_0_30px_rgba(16,185,129,0.05)] bg-[#0A0A0A] overflow-hidden flex flex-col h-[700px]">
          <div className="px-4 py-3 bg-[#111] border-b border-[#222] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Terminal className="h-4 w-4 text-emerald-500"/>
              <h2 className="text-sm font-mono font-bold text-emerald-500 tracking-wider">SYSTEM_LOGS_tty1</h2>
            </div>
            <div className="flex gap-1.5">
              <div className="w-3 h-3 rounded-full bg-red-500/80" />
              <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
              <div className="w-3 h-3 rounded-full bg-emerald-500/80" />
            </div>
          </div>
          <div className="flex-1 overflow-auto custom-scrollbar p-4 space-y-2 font-mono text-[11px] leading-relaxed">
            <div className="text-slate-500 mb-4">
              [SYSTEM] Initialising secure websocket connection to redis channel task_{taskId.split("-")[0]}...<br/>
              [SYSTEM] Connection authenticated via JWT.<br/>
              [SYSTEM] Tail starting...
            </div>
            {events.length === 0 ? (
              <p className="text-emerald-500/50 animate-pulse">_</p>
            ) : events.slice(-100).map((ev: WSEvent, i: number) => (
              <div key={i} className="flex gap-3 animate-fade-in hover:bg-white/[0.02] px-1 rounded transition-colors break-words">
                <span className="text-slate-600 shrink-0 select-none">
                  {ev.timestamp ? new Date(ev.timestamp).toISOString().split("T")[1].replace("Z", "") : "00:00:00.000"}
                </span>
                <span className={`${
                  ev.event.includes("error") ? "text-red-400" :
                  ev.event.includes("complete") ? "text-emerald-400" :
                  ev.event.includes("start") ? "text-blue-400" :
                  "text-slate-300"
                }`}>
                  {ev.event}
                </span>
              </div>
            ))}
            {connected && <div className="text-emerald-500 animate-pulse mt-2">_</div>}
          </div>
        </div>
      </div>

      {/* Final Executive Report */}
      {result?.report && (
        <motion.div initial={{opacity:0,y:30}} animate={{opacity:1,y:0}} transition={{delay:0.3, duration:0.6}} className="glass-card mt-8 p-8 md:p-12 border-t-4 border-t-purple-500">
          <div className="flex items-center gap-3 mb-8 pb-6 border-b border-white/10">
            <div className="w-12 h-12 rounded-xl bg-purple-500/10 flex items-center justify-center">
              <FileText className="h-6 w-6 text-purple-400"/>
            </div>
            <div>
              <h2 className="text-2xl font-black text-white tracking-tight">Executive Synthetis Report</h2>
              <p className="text-sm font-mono text-purple-300 mt-1">Status: Verified via Critic Agent</p>
            </div>
          </div>
          
          <div className="prose prose-invert prose-lg max-w-none 
            prose-headings:text-slate-100 prose-headings:font-bold prose-headings:tracking-tight
            prose-p:text-slate-300 prose-p:leading-relaxed
            prose-a:text-brand-400 prose-a:no-underline hover:prose-a:underline
            prose-strong:text-white prose-strong:font-bold
            prose-ul:text-slate-300
            prose-code:text-emerald-300 prose-code:bg-emerald-500/10 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:font-mono prose-code:text-sm prose-code:before:content-none prose-code:after:content-none
            prose-pre:bg-[#0A0A0A] prose-pre:border prose-pre:border-white/10 prose-pre:shadow-xl
            prose-blockquote:border-l-brand-500 prose-blockquote:bg-brand-500/5 prose-blockquote:py-1 prose-blockquote:pr-4 prose-blockquote:rounded-r-lg">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {result.report.content}
            </ReactMarkdown>
          </div>
          
          {result.citations && result.citations.length > 0 && (
            <div className="mt-12 rounded-2xl bg-slate-900/60 border border-white/5 p-6">
              <h3 className="font-bold text-slate-200 mb-4 flex items-center gap-2">
                <FileText className="h-4 w-4"/> Source Citations ({result.citations.length})
              </h3>
              <div className="grid md:grid-cols-2 gap-3">
                {result.citations.map((c: any, i: number) => (
                  <div key={c.id} className="flex items-start gap-3 p-3 rounded-xl bg-slate-800/40 border border-white/5 hover:border-brand-500/30 transition-colors">
                    <span className="w-6 h-6 rounded bg-slate-700/50 flex items-center justify-center text-xs font-mono text-slate-400 shrink-0">
                      {i+1}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-200 truncate" title={c.title}>{c.title}</p>
                      {c.url && <a href={c.url} target="_blank" rel="noopener noreferrer" className="text-xs text-brand-400 hover:text-brand-300 truncate block mt-0.5">
                        {new URL(c.url).hostname} ↗
                      </a>}
                    </div>
                    {c.verified && (
                      <span title="Verified by Critic">
                        <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />
                      </span>
                    )}
                  </div>  
                ))}
              </div>
            </div>
          )}
        </motion.div>
      )}
    </div>
  );
}
