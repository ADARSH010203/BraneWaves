"use client";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, AlertTriangle } from "lucide-react";
import type { TaskStep } from "@/types";
import { getAgentBadgeClass } from "@/lib/utils";

interface AgentTimelineProps {
  steps: TaskStep[];
}

export function AgentTimeline({ steps }: AgentTimelineProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const toggleExpand = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
  };

  return (
    <div className="relative border-l-2 border-slate-700/50 ml-4 space-y-6 pb-4">
      <AnimatePresence>
        {steps.map((step: TaskStep, i: number) => (
          <motion.div
            key={step.id}
            initial={{ opacity: 0, y: 30, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{
              type: "spring",
              stiffness: 400,
              damping: 30,
              delay: Math.min(i * 0.05, 0.5), // Cap delay so live updates don't delay infinitely
            }}
            className="relative pl-8"
          >
            {/* Timeline Node */}
            <div
              className={`absolute -left-[11px] top-1.5 w-5 h-5 rounded-full border-4 border-slate-900 transition-colors duration-500 ${
                step.status === "completed"
                  ? "bg-emerald-500 shadow-[0_0_10px_#10b981]"
                  : step.status === "running"
                  ? "bg-blue-500 animate-[pulse-glow_2s_infinite] shadow-[0_0_15px_#3b82f6]"
                  : step.status === "failed"
                  ? "bg-red-500 shadow-[0_0_10px_#ef4444]"
                  : step.status === "skipped"
                  ? "bg-orange-500 shadow-[0_0_10px_#f97316]"
                  : "bg-slate-600"
              }`}
            />

            <div
              onClick={() => toggleExpand(step.id)}
              className={`bg-slate-800/40 border rounded-xl overflow-hidden transition-all duration-300 cursor-pointer group hover:bg-slate-800/60 ${
                expandedId === step.id ? "border-brand-500/50 shadow-[0_0_20px_rgba(99,102,241,0.1)]" : "border-white/5 hover:border-brand-500/30"
              }`}
            >
              {/* Card Header (Always visible) */}
              <div className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-3">
                <div className="flex flex-wrap items-center gap-3">
                  <span className="text-xs font-mono text-slate-500 w-6 shrink-0">#{step.order}</span>
                  <span className={getAgentBadgeClass(step.agent_type)}>{step.agent_type} agent</span>
                  
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider transition-colors ${
                      step.status === "completed"
                        ? "bg-emerald-500/10 text-emerald-400"
                        : step.status === "running"
                        ? "bg-blue-500/10 text-blue-400"
                        : step.status === "failed"
                        ? "bg-red-500/10 text-red-400"
                        : step.status === "skipped"
                        ? "bg-orange-500/10 text-orange-400"
                        : "bg-slate-500/10 text-slate-400"
                    }`}
                  >
                    {step.status}
                  </span>

                  {step.confidence != null && (
                    <span className="text-xs font-mono text-brand-300 bg-brand-500/10 px-2 py-1 rounded hidden sm:inline-block">
                      Conf: {(step.confidence * 100).toFixed(0)}%
                    </span>
                  )}
                </div>
                
                <div className="flex items-center gap-4 text-xs font-mono text-slate-500">
                  {step.completed_at && step.started_at && (
                    <span className="tracking-widest">
                      {((new Date(step.completed_at).getTime() - new Date(step.started_at).getTime()) / 1000).toFixed(1)}s
                    </span>
                  )}
                  <ChevronDown
                    className={`h-4 w-4 transition-transform duration-300 ${
                      expandedId === step.id ? "rotate-180 text-brand-400" : "text-slate-600 group-hover:text-brand-400"
                    }`}
                  />
                </div>
              </div>

              {/* Title Snippet */}
              <div className="px-4 pb-4">
                 <h4 className={`font-semibold text-sm leading-relaxed transition-colors ${expandedId === step.id ? "text-white" : "text-slate-300"} line-clamp-2`}>
                   {step.title}
                 </h4>
              </div>

              {/* Expanding Content */}
              <AnimatePresence>
                {expandedId === step.id && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.3, ease: "easeInOut" }}
                    className="overflow-hidden border-t border-white/5 bg-black/20"
                  >
                    <div className="p-4 space-y-4 text-sm text-slate-300">
                      
                      {step.description && (
                         <div>
                           <p className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-1">Objective</p>
                           <p className="leading-relaxed">{step.description}</p>
                         </div>
                      )}

                      {/* Error details if failed */}
                      {step.error && (
                        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-300 font-mono flex items-start gap-2">
                          <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                          <span className="break-all whitespace-pre-wrap">{step.error}</span>
                        </div>
                      )}

                      {/* Output Data */}
                      {step.output_data && Object.keys(step.output_data).length > 0 && (
                        <div>
                           <p className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-2">Agent Output Payload</p>
                           <pre className="p-3 rounded-lg bg-[#0A0A0A] border border-white/5 font-mono text-[11px] text-emerald-300/80 overflow-auto custom-scrollbar shadow-inner">
                             {JSON.stringify(step.output_data, null, 2)}
                           </pre>
                        </div>
                      )}

                      {/* Diagnostics */}
                      {step.status === "completed" && step.cost_usd != null && (
                         <div className="flex gap-4 pt-2 border-t border-white/5 text-xs font-mono">
                            <span className="text-amber-400">Tokens: {step.tokens || 0}</span>
                            <span className="text-emerald-400">Cost: ${step.cost_usd.toFixed(4)}</span>
                         </div>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
