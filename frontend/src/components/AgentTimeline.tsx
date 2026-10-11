"use client";
import { useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, AlertTriangle, GitBranch } from "lucide-react";
import type { TaskStep } from "@/types";
import { getAgentBadgeClass } from "@/lib/utils";

interface AgentTimelineProps {
  steps: TaskStep[];
}

const NODE_W = 190;
const NODE_H = 70;
const LEVEL_GAP = 140;
const X_GAP = 34;

const STATUS_STYLE: Record<string, { fill: string; stroke: string; text: string }> = {
  completed: { fill: "#052e2b", stroke: "#10b981", text: "#6ee7b7" },
  running: { fill: "#172554", stroke: "#3b82f6", text: "#93c5fd" },
  failed: { fill: "#450a0a", stroke: "#ef4444", text: "#fca5a5" },
  skipped: { fill: "#431407", stroke: "#f97316", text: "#fdba74" },
  retrying: { fill: "#3b0764", stroke: "#a855f7", text: "#d8b4fe" },
  pending: { fill: "#0f172a", stroke: "#475569", text: "#94a3b8" },
};

function buildDagLayout(steps: TaskStep[]) {
  const byId = new Map(steps.map(step => [step.id, step]));
  const levelMemo = new Map<string, number>();
  const visiting = new Set<string>();

  const levelOf = (step: TaskStep): number => {
    const cached = levelMemo.get(step.id);
    if (cached != null) return cached;
    if (visiting.has(step.id)) return 0;
    visiting.add(step.id);
    const validDeps = step.depends_on.filter(dep => byId.has(dep));
    const level = validDeps.length === 0
      ? 0
      : Math.max(...validDeps.map(dep => levelOf(byId.get(dep)!))) + 1;
    visiting.delete(step.id);
    levelMemo.set(step.id, level);
    return level;
  };

  const levels = new Map<number, TaskStep[]>();
  steps.forEach(step => {
    const level = levelOf(step);
    levels.set(level, [...(levels.get(level) || []), step]);
  });

  const maxPerLevel = Math.max(1, ...Array.from(levels.values()).map(items => items.length));
  const width = Math.max(760, maxPerLevel * NODE_W + (maxPerLevel + 1) * X_GAP);
  const maxLevel = Math.max(0, ...Array.from(levels.keys()));
  const height = Math.max(180, (maxLevel + 1) * LEVEL_GAP + 40);
  const positions = new Map<string, { x: number; y: number }>();

  Array.from(levels.entries()).forEach(([level, items]) => {
    const rowWidth = items.length * NODE_W + Math.max(0, items.length - 1) * X_GAP;
    const startX = (width - rowWidth) / 2;
    items
      .slice()
      .sort((a, b) => a.order - b.order)
      .forEach((step, index) => {
        positions.set(step.id, {
          x: startX + index * (NODE_W + X_GAP),
          y: 20 + level * LEVEL_GAP,
        });
      });
  });

  return { byId, positions, width, height };
}

export function AgentTimeline({ steps }: AgentTimelineProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const layout = useMemo(() => buildDagLayout(steps), [steps]);

  if (steps.length === 0) {
    return <div className="text-sm text-slate-500">No execution steps yet.</div>;
  }

  return (
    <div className="space-y-8">
      <div className="rounded-2xl border border-white/5 bg-slate-950/60 overflow-auto">
        <div className="px-4 py-3 border-b border-white/5 flex items-center gap-2 text-sm text-slate-300">
          <GitBranch className="h-4 w-4 text-brand-400" />
          <span className="font-semibold">Live dependency DAG</span>
          <span className="text-xs text-slate-500">— arrows show actual depends_on relationships</span>
        </div>
        <svg
          viewBox={`0 0 ${layout.width} ${layout.height}`}
          className="w-full min-w-[760px]"
          style={{ minHeight: Math.min(layout.height, 620) }}
          role="img"
          aria-label="Agent execution dependency graph"
        >
          <defs>
            <marker id="dag-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
              <path d="M0,0 L8,4 L0,8 z" fill="#64748b" />
            </marker>
          </defs>

          {steps.flatMap(step => {
            const target = layout.positions.get(step.id);
            if (!target) return [];
            return step.depends_on.map(depId => {
              const source = layout.positions.get(depId);
              if (!source) return null;
              const sx = source.x + NODE_W / 2;
              const sy = source.y + NODE_H;
              const tx = target.x + NODE_W / 2;
              const ty = target.y;
              const midY = (sy + ty) / 2;
              return (
                <path
                  key={`${depId}-${step.id}`}
                  d={`M ${sx} ${sy} C ${sx} ${midY}, ${tx} ${midY}, ${tx} ${ty}`}
                  fill="none"
                  stroke="#475569"
                  strokeWidth="2"
                  strokeOpacity="0.8"
                  markerEnd="url(#dag-arrow)"
                />
              );
            });
          })}

          {steps.map(step => {
            const pos = layout.positions.get(step.id);
            if (!pos) return null;
            const style = STATUS_STYLE[step.status] || STATUS_STYLE.pending;
            const shortTitle = step.title.length > 28 ? `${step.title.slice(0, 27)}…` : step.title;
            return (
              <g
                key={step.id}
                transform={`translate(${pos.x}, ${pos.y})`}
                onClick={() => setExpandedId(step.id)}
                className="cursor-pointer"
              >
                <rect
                  width={NODE_W}
                  height={NODE_H}
                  rx="12"
                  fill={style.fill}
                  stroke={style.stroke}
                  strokeWidth={expandedId === step.id ? 3 : 1.5}
                />
                <text x="14" y="23" fill="#f8fafc" fontSize="12" fontWeight="700">
                  {shortTitle}
                </text>
                <text x="14" y="43" fill="#94a3b8" fontSize="10">
                  {step.agent_type.toUpperCase()}
                </text>
                <text x={NODE_W - 14} y="43" fill={style.text} fontSize="10" textAnchor="end" fontWeight="700">
                  {step.status.toUpperCase()}
                </text>
                <text x="14" y="59" fill="#64748b" fontSize="9">
                  {step.depends_on.length === 0 ? "ROOT" : `${step.depends_on.length} dependenc${step.depends_on.length === 1 ? "y" : "ies"}`}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      <div className="space-y-4">
        <AnimatePresence>
          {steps.slice().sort((a, b) => a.order - b.order).map((step, i) => {
            const dependencyTitles = step.depends_on
              .map(id => layout.byId.get(id)?.title)
              .filter(Boolean) as string[];
            return (
              <motion.div
                key={step.id}
                initial={{ opacity: 0, y: 18 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ delay: Math.min(i * 0.03, 0.3) }}
                className={`rounded-xl border overflow-hidden bg-slate-800/35 ${
                  expandedId === step.id ? "border-brand-500/50" : "border-white/5"
                }`}
              >
                <button
                  type="button"
                  onClick={() => setExpandedId(expandedId === step.id ? null : step.id)}
                  className="w-full p-4 text-left flex items-center justify-between gap-4 hover:bg-white/[0.02]"
                >
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-2">
                      <span className="text-xs font-mono text-slate-500">#{step.order + 1}</span>
                      <span className={getAgentBadgeClass(step.agent_type)}>{step.agent_type} agent</span>
                      <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400">{step.status}</span>
                    </div>
                    <h4 className="font-semibold text-sm text-slate-200">{step.title}</h4>
                    {dependencyTitles.length > 0 && (
                      <p className="text-xs text-slate-500 mt-1">
                        Depends on: {dependencyTitles.join(" • ")}
                      </p>
                    )}
                  </div>
                  <ChevronDown className={`h-4 w-4 shrink-0 transition-transform ${expandedId === step.id ? "rotate-180 text-brand-400" : "text-slate-500"}`} />
                </button>

                <AnimatePresence>
                  {expandedId === step.id && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="overflow-hidden border-t border-white/5 bg-black/20"
                    >
                      <div className="p-4 space-y-4 text-sm text-slate-300">
                        {step.description && (
                          <div>
                            <p className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-1">Objective</p>
                            <p className="leading-relaxed">{step.description}</p>
                          </div>
                        )}
                        {step.error && (
                          <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-300 font-mono flex items-start gap-2">
                            <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                            <span className="break-all whitespace-pre-wrap">{step.error}</span>
                          </div>
                        )}
                        {step.output_data && Object.keys(step.output_data).length > 0 && (
                          <div>
                            <p className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-2">Agent Output Payload</p>
                            <pre className="p-3 rounded-lg bg-[#0A0A0A] border border-white/5 font-mono text-[11px] text-emerald-300/80 overflow-auto custom-scrollbar">
                              {JSON.stringify(step.output_data, null, 2)}
                            </pre>
                          </div>
                        )}
                        {step.status === "completed" && (
                          <div className="flex gap-4 pt-2 border-t border-white/5 text-xs font-mono">
                            <span className="text-amber-400">Tokens: {step.tokens || step.output_data?.tokens?.total || 0}</span>
                            <span className="text-emerald-400">Step cost: ${(step.cost_usd || 0).toFixed(4)}</span>
                          </div>
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </div>
  );
}
