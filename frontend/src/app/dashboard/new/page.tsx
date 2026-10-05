/* ─── ARC Platform — Premium New Task Page ────────────────────────────────── */
"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { useTask } from "@/hooks/useTask";
import { api } from "@/lib/api";
import { ArrowRight, ArrowLeft, AlertCircle, Rocket, FileText, Settings2, CheckCircle2, X, Sparkles, Brain } from "lucide-react";

const STEPS = [
  { label: "Describe", icon: FileText, desc: "Define your research objective" },
  { label: "Configure", icon: Settings2, desc: "Set budget and tags" },
  { label: "Launch", icon: Rocket, desc: "Review and deploy agents" },
];

export default function NewTaskPage() {
  const router = useRouter();
  const { createTask, loading } = useTask();
  const [step, setStep] = useState(0);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [budget, setBudget] = useState(5);
  const [tags, setTags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState("");
  const [error, setError] = useState("");
  const [templates, setTemplates] = useState<any[]>([]);
  const [memoryResults, setMemoryResults] = useState<any[]>([]);

  useEffect(() => {
    async function loadTemplates() {
      try {
        const res = await api.getTemplates();
        setTemplates(res.data || []);
      } catch (err) {
        console.error("Failed to load templates", err);
      }
    }
    loadTemplates();
  }, []);

  // Debounced memory search
  useEffect(() => {
    if (description.length < 20) {
      setMemoryResults([]);
      return;
    }
    const timer = setTimeout(async () => {
      try {
        const data = await api.searchMemory(description);
        setMemoryResults(data.results.filter((r: any) => r.score > 0.5));
      } catch {
        setMemoryResults([]);
      }
    }, 800);
    return () => clearTimeout(timer);
  }, [description]);

  const selectTemplate = (t: any) => {
    setTitle(t.title);
    setDescription(t.example_prompts[0] || t.description);
    setBudget(t.suggested_budget);
    setTags(t.suggested_tags);
  };

  const addTag = () => {
    const t = tagInput.trim();
    if (t && !tags.includes(t)) { setTags([...tags, t]); setTagInput(""); }
  };

  const removeTag = (tag: string) => setTags(tags.filter(t => t !== tag));

  const handleSubmit = async () => {
    setError("");
    try {
      const task = await createTask(title, description, budget, tags);
      router.push(`/dashboard/tasks/${task.id}`);
    } catch (e: any) { setError(e.message || "Failed"); }
  };

  const budgetPercent = ((budget - 0.5) / (50 - 0.5)) * 100;

  return (
    <div className="max-w-3xl mx-auto animate-fade-in">
      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center gap-3 mb-2">
          <Sparkles className="h-6 w-6 text-brand-400" />
          <h1 className="text-3xl md:text-4xl font-black text-white tracking-tight">Deploy Research Task</h1>
        </div>
        <p className="text-slate-400 text-lg">Define your objective and let the 7-agent pipeline handle the rest.</p>
      </div>

      {/* Premium Stepper */}
      <div className="glass-card p-6 mb-8">
        <div className="flex items-center justify-between">
          {STEPS.map((s, i) => (
            <div key={s.label} className="flex items-center flex-1">
              <div className="flex flex-col items-center gap-2 relative z-10">
                <div className={`w-12 h-12 rounded-2xl flex items-center justify-center transition-all duration-500 ${
                  i < step ? "bg-emerald-500/20 border border-emerald-500/30 shadow-[0_0_15px_rgba(16,185,129,0.2)]" :
                  i === step ? "bg-brand-500/20 border border-brand-500/30 shadow-[0_0_20px_rgba(99,102,241,0.3)] scale-110" :
                  "bg-slate-800/50 border border-white/5"
                }`}>
                  {i < step ? (
                    <CheckCircle2 className="h-6 w-6 text-emerald-400" />
                  ) : (
                    <s.icon className={`h-6 w-6 ${i === step ? "text-brand-400" : "text-slate-500"}`} />
                  )}
                </div>
                <div className="text-center">
                  <p className={`text-xs font-bold ${i === step ? "text-white" : i < step ? "text-emerald-400" : "text-slate-500"}`}>{s.label}</p>
                  <p className="text-[10px] text-slate-600 hidden sm:block">{s.desc}</p>
                </div>
              </div>
              {i < 2 && (
                <div className="flex-1 mx-4 h-1 rounded-full bg-slate-800 overflow-hidden">
                  <div className={`h-full rounded-full transition-all duration-700 ${
                    i < step ? "bg-gradient-to-r from-emerald-500 to-emerald-400 w-full" : "bg-transparent w-0"
                  }`} />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {error && (
        <motion.div initial={{opacity:0, y:-10}} animate={{opacity:1, y:0}}
          className="flex items-center gap-2 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm mb-6">
          <AlertCircle className="h-4 w-4" />{error}
        </motion.div>
      )}

      {/* Step Content */}
      <AnimatePresence mode="wait">
        <motion.div key={step} initial={{opacity:0, x:30}} animate={{opacity:1, x:0}} exit={{opacity:0, x:-30}}
          transition={{duration:0.3}} className="glass-card p-8">
          
          {step === 0 && (
            <div className="space-y-8">
              {/* Template Selector */}
              {templates.length > 0 && (
                <div className="mb-6">
                  <label className="block text-sm font-bold mb-3 text-white">Start with a Template <span className="text-slate-500 font-normal">(Optional)</span></label>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                    {templates.map(t => (
                      <div key={t.id} onClick={() => selectTemplate(t)}
                        className="p-4 rounded-xl border border-white/5 bg-slate-900/50 hover:bg-slate-800 hover:border-brand-500/30 cursor-pointer transition-all group">
                        <h4 className="font-bold text-slate-200 text-sm group-hover:text-brand-400 transition-colors mb-1">{t.title}</h4>
                        <p className="text-xs text-slate-500 line-clamp-2">{t.description}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div>
                <label className="block text-sm font-bold mb-3 text-white">Research Title</label>
                <input value={title} onChange={e => setTitle(e.target.value)} className="input-field text-base"
                  placeholder="e.g. Analyse quantum error correction techniques" />
              </div>
              <div>
                <label className="block text-sm font-bold mb-3 text-white">Description</label>
                <textarea value={description} onChange={e => setDescription(e.target.value)}
                  className="input-field min-h-[180px] text-base" rows={7}
                  placeholder="Describe your research objective in detail. The more specific, the better the agents will perform..." />
                <p className="text-xs text-slate-500 mt-2">{description.length} characters</p>

                {memoryResults.length > 0 && (
                  <div className="mt-3 p-3 rounded-xl bg-purple-500/10 border border-purple-500/20">
                    <p className="text-xs font-medium text-purple-300 mb-2 flex items-center gap-1.5">
                      <Brain className="h-3.5 w-3.5" />
                      ARC Brain: {memoryResults.length} related memories found
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {memoryResults.map((m: any, i: number) => (
                        <span key={i} className="text-xs px-2 py-1 bg-purple-500/10 text-purple-300 rounded-lg border border-purple-500/20">
                          {m.label}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
              <div className="flex justify-end">
                <button onClick={() => setStep(1)} disabled={!title || !description}
                  className="btn-brand flex items-center gap-2 disabled:opacity-40 px-8">
                  Next <ArrowRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}

          {step === 1 && (
            <div className="space-y-8">
              <div>
                <label className="block text-sm font-bold mb-4 text-white">
                  Budget Limit: <span className="text-brand-400 text-lg">${budget.toFixed(2)}</span>
                </label>
                <div className="relative">
                  <div className="h-3 rounded-full bg-slate-800 overflow-hidden mb-2">
                    <div className="h-full rounded-full bg-gradient-to-r from-brand-500 via-purple-500 to-cyan-500 transition-all duration-300"
                      style={{ width: `${budgetPercent}%` }} />
                  </div>
                  <input type="range" min={0.5} max={50} step={0.5} value={budget}
                    onChange={e => setBudget(parseFloat(e.target.value))}
                    className="w-full absolute top-0 h-3 opacity-0 cursor-pointer" />
                  <div className="flex justify-between text-xs text-slate-500 mt-1">
                    <span>$0.50</span><span>$25.00</span><span>$50.00</span>
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-sm font-bold mb-3 text-white">Tags</label>
                <div className="flex gap-2 mb-3">
                  <input value={tagInput} onChange={e => setTagInput(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && (e.preventDefault(), addTag())}
                    className="input-field flex-1" placeholder="Type a tag and press Enter" />
                  <button onClick={addTag} className="btn-ghost px-4 text-sm">Add</button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {tags.map(tag => (
                    <span key={tag} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-brand-500/10 border border-brand-500/20 text-brand-300 text-xs font-semibold">
                      {tag}
                      <button onClick={() => removeTag(tag)} className="hover:text-red-400 transition-colors"><X className="h-3 w-3" /></button>
                    </span>
                  ))}
                  {tags.length === 0 && <p className="text-xs text-slate-500">No tags added (optional)</p>}
                </div>
              </div>

              <div className="flex justify-between">
                <button onClick={() => setStep(0)} className="btn-ghost flex items-center gap-2"><ArrowLeft className="h-4 w-4" />Back</button>
                <button onClick={() => setStep(2)} className="btn-brand flex items-center gap-2 px-8">Review <ArrowRight className="h-4 w-4" /></button>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-6">
              <h2 className="text-xl font-bold text-white mb-4">Deployment Summary</h2>
              <div className="rounded-xl bg-slate-800/40 border border-white/5 divide-y divide-white/5">
                <div className="flex justify-between px-5 py-4">
                  <span className="text-slate-400 text-sm font-medium">Title</span>
                  <span className="font-bold text-white text-sm text-right max-w-xs truncate">{title}</span>
                </div>
                <div className="flex justify-between px-5 py-4">
                  <span className="text-slate-400 text-sm font-medium">Budget</span>
                  <span className="font-bold text-brand-400 text-sm">${budget.toFixed(2)} USD</span>
                </div>
                <div className="flex justify-between px-5 py-4">
                  <span className="text-slate-400 text-sm font-medium">Tags</span>
                  <div className="flex flex-wrap gap-1 justify-end">
                    {tags.length > 0 ? tags.map(t => (
                      <span key={t} className="px-2 py-0.5 rounded bg-brand-500/10 text-brand-300 text-xs">{t}</span>
                    )) : <span className="text-slate-500 text-xs">None</span>}
                  </div>
                </div>
                <div className="px-5 py-4">
                  <span className="text-slate-400 text-sm font-medium block mb-2">Description</span>
                  <p className="text-slate-300 text-sm leading-relaxed">{description}</p>
                </div>
              </div>

              <div className="rounded-xl bg-brand-500/5 border border-brand-500/20 p-4 text-sm text-brand-300">
                <p className="font-semibold mb-1">🚀 What happens next?</p>
                <p className="text-slate-400">The Planner agent will decompose your task into a DAG, then Research, Code, Data, Critic, and Report agents will execute in parallel.</p>
              </div>

              <div className="flex justify-between">
                <button onClick={() => setStep(1)} className="btn-ghost flex items-center gap-2"><ArrowLeft className="h-4 w-4" />Back</button>
                <button onClick={handleSubmit} disabled={loading}
                  className="btn-brand flex items-center gap-2 px-8 shadow-[0_0_30px_rgba(99,102,241,0.3)]">
                  {loading ? <div className="h-5 w-5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> :
                    <><Rocket className="h-5 w-5" />Deploy Agents</>}
                </button>
              </div>
            </div>
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
