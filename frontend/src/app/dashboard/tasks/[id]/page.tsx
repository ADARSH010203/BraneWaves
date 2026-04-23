"use client";
import { ReportChat } from "@/components/ReportChat";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { useTask } from "@/hooks/useTask";
import { useWebSocket } from "@/hooks/useWebSocket";
import { api } from "@/lib/api";
import { formatDate, formatCost, getStatusColor, getAgentBadgeClass, cn } from "@/lib/utils";
import {
  Activity, FileText, DollarSign, CheckCircle2, AlertTriangle, Clock, Wifi, Terminal,
  Download, FileDown, XCircle, Loader2, ChevronDown, Ban,
} from "lucide-react";
import type { TaskStep, WSEvent } from "@/types";
import { AgentTimelineSkeleton } from "@/components/skeletons/AgentTimelineSkeleton";
import { DashboardSkeleton } from "@/components/skeletons/DashboardSkeleton";
import { AgentTimeline } from "@/components/AgentTimeline";

export default function TaskDetailPage() {
  const params = useParams();
  const taskId = params?.id as string;
  const {
    currentTask, steps, result,
    fetchTask, fetchSteps, fetchResult,
    loading, cancelTask,
  } = useTask();
  const { events, connected, latestEvent } = useWebSocket(
    currentTask?.status === "running" || currentTask?.status === "planning" ? taskId : null
  );

  // ── Export state ────────────────────────────────────────────────────
  const [exportDropdownOpen, setExportDropdownOpen] = useState(false);
  const [exporting, setExporting] = useState<"pdf" | "docx" | null>(null);

  const [showCancelModal, setShowCancelModal] = useState(false);
  const [cancelling, setCancelling] = useState(false);

  // ── Tab state ──────────────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState<"timeline" | "report" | "cost" | "raw">("timeline");

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

  // Close export dropdown on outside click
  useEffect(() => {
    if (!exportDropdownOpen) return;
    const handler = () => setExportDropdownOpen(false);
    document.addEventListener("click", handler);
    return () => document.removeEventListener("click", handler);
  }, [exportDropdownOpen]);

  // ── Export handler ─────────────────────────────────────────────────
  const handleExport = async (format: "pdf" | "docx") => {
    setExporting(format);
    setExportDropdownOpen(false);
    try {
      await api.exportReport(taskId, format);
    } catch (err: any) {
      console.error("Export failed:", err);
      alert(`Export failed: ${err.message || "Unknown error"}`);
    } finally {
      setExporting(null);
    }
  };

  // ── Cancel handler ─────────────────────────────────────────────────
  const handleCancel = async () => {
    setCancelling(true);
    try {
      await cancelTask(taskId);
      setShowCancelModal(false);
    } catch (err: any) {
      console.error("Cancel failed:", err);
      alert(`Failed to cancel: ${err.message || "Unknown error"}`);
    } finally {
      setCancelling(false);
    }
  };

  // ── Status badge helper ────────────────────────────────────────────
  const getStatusBadge = (status: string) => {
    const map: Record<string, string> = {
      running: "bg-blue-500/20 text-blue-400 border-blue-500/30 animate-pulse",
      planning: "bg-blue-500/20 text-blue-400 border-blue-500/30 animate-pulse",
      completed: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
      failed: "bg-red-500/20 text-red-400 border-red-500/30",
      cancelled: "bg-orange-500/20 text-orange-400 border-orange-500/30",
      pending: "bg-amber-500/20 text-amber-400 border-amber-500/30",
      paused: "bg-amber-500/20 text-amber-400 border-amber-500/30",
    };
    return map[status] || "bg-slate-500/20 text-slate-400 border-slate-500/30";
  };

  const isCancellable = currentTask?.status === "running" || currentTask?.status === "planning";

  const budgetMax = currentTask?.budget?.max_usd ?? 5;
  const budgetSpent = currentTask?.budget?.spent_usd ?? 0;
  const budgetPercent = Math.min((budgetSpent / budgetMax) * 100, 100);

  if (loading && !currentTask) return (
    <DashboardSkeleton />
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
      <div className="glass-card p-6 mb-8 border-l-4 border-l-brand-500">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-2xl md:text-3xl font-black text-white tracking-tight">{currentTask.title}</h1>
              <span className={`px-3 py-1 text-xs font-bold uppercase tracking-wider rounded-full backdrop-blur-md border ${getStatusBadge(currentTask.status)}`}>
                {currentTask.status}
              </span>
            </div>
            <p className="text-slate-400 text-sm md:text-base max-w-2xl leading-relaxed">{currentTask.description}</p>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            {/* Cancel Button (FEAT-02) */}
            {isCancellable && (
              <button
                id="cancel-task-btn"
                onClick={() => setShowCancelModal(true)}
                className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium border transition-all
                  bg-red-500/10 text-red-400 border-red-500/20 hover:bg-red-500/20 hover:border-red-500/40 hover:shadow-[0_0_15px_rgba(239,68,68,0.15)]"
              >
                <XCircle className="h-4 w-4" />
                Cancel Task
              </button>
            )}

            {/* Cancelled indicator */}
            {currentTask.status === "cancelled" && (
              <div className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium border bg-orange-500/10 text-orange-400 border-orange-500/20">
                <Ban className="h-4 w-4" />
                Cancelled
              </div>
            )}

            {/* WebSocket status indicator */}
            <div className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium border transition-colors ${
              connected ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20 shadow-[0_0_15px_rgba(16,185,129,0.15)]" : "bg-slate-800/50 text-slate-400 border-slate-700"
            }`}>
              <Wifi className={`h-4 w-4 ${connected ? "animate-pulse" : ""}`} />
              {connected ? "Stream Live" : "Stream Offline"}
            </div>
          </div>
        </div>
        
        {/* Change #5: Live Cost Meter */}
        {(currentTask.status === "running" || currentTask.status === "planning") && (
          <div className="mt-4 pt-4 border-t border-white/5">
            <div className="flex items-center justify-between text-xs mb-1.5">
              <span className="text-slate-400">Budget used</span>
              <span className="font-mono text-amber-400">
                ${budgetSpent.toFixed(4)} / ${budgetMax.toFixed(2)}
              </span>
            </div>
            <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
              <div
                className={cn(
                  "h-full rounded-full transition-all duration-1000",
                  budgetPercent > 80 ? "bg-red-400" :
                  budgetPercent > 50 ? "bg-amber-400" : "bg-brand-500"
                )}
                style={{ width: `${budgetPercent}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Tab Bar */}
      <div className="flex gap-1 mb-6 glass-card p-1.5 w-fit">
        {[
          { id: "timeline", label: "Timeline", icon: Activity },
          { id: "report",   label: "Report",   icon: FileText },
          { id: "cost",     label: "Cost",     icon: DollarSign },
          { id: "raw",      label: "Raw JSON", icon: Terminal },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all",
              activeTab === tab.id
                ? "bg-brand-500/20 text-brand-300 border border-brand-500/30"
                : "text-slate-400 hover:text-white hover:bg-white/5"
            )}
          >
            <tab.icon className="h-4 w-4" />
            {tab.label}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.2 }}
        >
          {activeTab === "timeline" && (
            <div>
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
              <AgentTimelineSkeleton />
            ) : (
              <AgentTimeline steps={steps} />
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
                  ev.event.includes("error") || ev.status === "failed" ? "text-red-400" :
                  ev.status === "cancelled" ? "text-orange-400" :
                  ev.event.includes("complete") || ev.status === "completed" ? "text-emerald-400" :
                  ev.event.includes("start") ? "text-blue-400" :
                  "text-slate-300"
                }`}>
                  {ev.status === "cancelled" ? `[CANCELLED] ${ev.message || "Task cancelled by user"}` : ev.event}
                  {ev.status && !ev.status.toString().includes("cancelled") ? ` → ${ev.status}` : ""}
                </span>
              </div>
            ))}
            {connected && <div className="text-emerald-500 animate-pulse mt-2">_</div>}
          </div>
        </div>
              </div>
            </div>
          )}

          {activeTab === "report" && (
            <div>
              {/* Final Executive Report */}
              {result?.report ? (
                <motion.div initial={{opacity:0,y:30}} animate={{opacity:1,y:0}} transition={{delay:0.3, duration:0.6}} className="glass-card mt-8 p-8 md:p-12 border-t-4 border-t-purple-500">
          <div className="flex items-center justify-between gap-3 mb-8 pb-6 border-b border-white/10">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-purple-500/10 flex items-center justify-center">
                <FileText className="h-6 w-6 text-purple-400"/>
              </div>
              <div>
                <h2 className="text-2xl font-black text-white tracking-tight">Executive Synthesis Report</h2>
                <p className="text-sm font-mono text-purple-300 mt-1">Status: Verified via Critic Agent</p>
              </div>
            </div>

            {/* FEAT-01: Export Dropdown */}
            <div className="relative">
              <button
                id="export-report-btn"
                onClick={(e) => { e.stopPropagation(); setExportDropdownOpen(!exportDropdownOpen); }}
                disabled={!!exporting}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold border transition-all
                  bg-purple-500/10 text-purple-300 border-purple-500/20
                  hover:bg-purple-500/20 hover:border-purple-500/40 hover:shadow-[0_0_20px_rgba(168,85,247,0.15)]
                  disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {exporting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Generating {exporting.toUpperCase()}...
                  </>
                ) : (
                  <>
                    <Download className="h-4 w-4" />
                    Export Report
                    <ChevronDown className={`h-3 w-3 transition-transform ${exportDropdownOpen ? "rotate-180" : ""}`} />
                  </>
                )}
              </button>

              <AnimatePresence>
                {exportDropdownOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: -5, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -5, scale: 0.95 }}
                    transition={{ duration: 0.15 }}
                    className="absolute right-0 mt-2 w-52 rounded-xl bg-slate-800 border border-white/10 shadow-2xl overflow-hidden z-50"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <button
                      id="export-pdf-btn"
                      onClick={() => handleExport("pdf")}
                      className="w-full flex items-center gap-3 px-4 py-3 text-sm text-slate-200 hover:bg-purple-500/10 hover:text-purple-300 transition-colors"
                    >
                      <FileDown className="h-4 w-4 text-red-400" />
                      <div className="text-left">
                        <p className="font-medium">Download as PDF</p>
                        <p className="text-xs text-slate-500">Formatted document</p>
                      </div>
                    </button>
                    <div className="border-t border-white/5" />
                    <button
                      id="export-docx-btn"
                      onClick={() => handleExport("docx")}
                      className="w-full flex items-center gap-3 px-4 py-3 text-sm text-slate-200 hover:bg-purple-500/10 hover:text-purple-300 transition-colors"
                    >
                      <FileDown className="h-4 w-4 text-blue-400" />
                      <div className="text-left">
                        <p className="font-medium">Download as Word</p>
                        <p className="text-xs text-slate-500">Editable DOCX file</p>
                      </div>
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>
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
            <ReactMarkdown 
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeHighlight]}
            >
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
                        {(() => { try { return new URL(c.url).hostname; } catch { return c.url; } })()} ↗
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

          <div className="mt-12">
            <h3 className="font-bold text-slate-200 mb-4 flex items-center gap-2 text-lg">
              <Terminal className="h-5 w-5 text-brand-400" /> Follow-up Chat
            </h3>
            <ReportChat taskId={taskId} />
          </div>
                </motion.div>
              ) : (
                <div className="glass-card p-12 text-center text-slate-400">
                  <FileText className="h-12 w-12 mx-auto mb-4 text-slate-600" />
                  <p>No report has been generated yet for this task.</p>
                </div>
              )}
            </div>
          )}

          {activeTab === "cost" && (
            <div className="glass-card overflow-hidden">
              <div className="px-6 py-4 border-b border-white/10">
                <h3 className="text-lg font-bold text-white">Cost Breakdown by Agent</h3>
              </div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/5 text-slate-400 text-xs uppercase tracking-wider">
                    <th className="px-6 py-3 text-left">Agent</th>
                    <th className="px-6 py-3 text-right">Tokens</th>
                    <th className="px-6 py-3 text-right">Cost (USD)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {steps?.map(step => (
                    <tr key={step.id} className="hover:bg-slate-800/20">
                      <td className="px-6 py-3 text-slate-200 capitalize">{step.agent_type}</td>
                      <td className="px-6 py-3 text-right font-mono text-slate-400">
                        {step.output_data?.tokens?.total?.toLocaleString() ?? "—"}
                      </td>
                      <td className="px-6 py-3 text-right font-mono text-amber-400">
                        ${(step.cost_usd ?? 0).toFixed(5)}
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="border-t border-white/10 bg-slate-900/30">
                    <td className="px-6 py-3 font-bold text-white">Total</td>
                    <td className="px-6 py-3 text-right font-mono text-slate-300">—</td>
                    <td className="px-6 py-3 text-right font-mono font-bold text-amber-400">
                      ${steps?.reduce((s, t) => s + (t.cost_usd ?? 0), 0).toFixed(5)}
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>
          )}

          {activeTab === "raw" && (
            <div className="glass-card p-6">
              <h3 className="text-lg font-bold text-white mb-4">Raw Step Outputs (JSON)</h3>
              <pre className="bg-slate-900/80 rounded-xl p-4 text-xs font-mono text-slate-300 overflow-auto max-h-[600px] custom-scrollbar">
                {JSON.stringify(
                  steps?.map(s => ({ id: s.id, type: s.agent_type, output: s.output_data })),
                  null, 2
                )}
              </pre>
            </div>
          )}
        </motion.div>
      </AnimatePresence>

      {/* ── FEAT-02: Cancel Confirmation Modal ───────────────────────────── */}
      <AnimatePresence>
        {showCancelModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm"
            onClick={() => !cancelling && setShowCancelModal(false)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0, y: 20 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.9, opacity: 0, y: 20 }}
              transition={{ type: "spring", damping: 25, stiffness: 350 }}
              className="bg-slate-900 border border-white/10 rounded-2xl p-8 max-w-md w-full mx-4 shadow-2xl"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 rounded-full bg-red-500/10 flex items-center justify-center">
                  <XCircle className="h-6 w-6 text-red-400" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">Cancel Task?</h3>
                  <p className="text-sm text-slate-400">This action cannot be undone</p>
                </div>
              </div>

              <p className="text-slate-300 text-sm mb-6 leading-relaxed">
                This will stop the AI agents from executing any remaining steps. 
                Steps that have already completed will be preserved, but no report 
                will be generated.
              </p>

              <div className="flex gap-3 justify-end">
                <button
                  id="cancel-modal-dismiss"
                  onClick={() => setShowCancelModal(false)}
                  disabled={cancelling}
                  className="px-5 py-2.5 rounded-xl text-sm font-medium border border-white/10 text-slate-300 
                    hover:bg-slate-800 hover:border-white/20 transition-colors disabled:opacity-50"
                >
                  Keep Running
                </button>
                <button
                  id="cancel-modal-confirm"
                  onClick={handleCancel}
                  disabled={cancelling}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold border transition-all
                    bg-red-500/20 text-red-400 border-red-500/30 
                    hover:bg-red-500/30 hover:border-red-500/50 hover:shadow-[0_0_20px_rgba(239,68,68,0.2)]
                    disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {cancelling ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Cancelling...
                    </>
                  ) : (
                    <>
                      <XCircle className="h-4 w-4" />
                      Yes, Cancel Task
                    </>
                  )}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
