/* ─── ARC Platform — Premium Landing Page ─────────────────────────────────── */
"use client";
import Link from "next/link";
import { motion } from "framer-motion";
import {
    Brain, Cpu, FileSearch, BarChart3, Shield, Zap,
    ArrowRight, CheckCircle2, Sparkles, GitBranch,
    TerminalSquare, Activity
} from "lucide-react";

const fadeUp = {
    hidden: { opacity: 0, y: 40 },
    visible: (i: number) => ({
        opacity: 1, y: 0,
        transition: { delay: i * 0.1, duration: 0.8, ease: [0.16, 1, 0.3, 1] },
    }),
};

const features = [
    { icon: Brain, title: "Agentic AI", desc: "7 autonomous agents — Planner, Researcher, Data, Code, Critic, Report, Repair — orchestrated dynamically." },
    { icon: GitBranch, title: "Graph Workflows", desc: "Automatic task decomposition into parallel and sequential step graphs with dependency resolution." },
    { icon: FileSearch, title: "Local Vector RAG", desc: "Upload PDFs/Data. Built-in ultra-fast FAISS vector search running entirely on your local machine." },
    { icon: TerminalSquare, title: "Sandboxed Python", desc: "The Code agent generates, executes, and validates Python natively in a secure isolated environment." },
    { icon: Activity, title: "Real-time Streaming", desc: "Watch the agents think, plan, and execute live via WebSockets and Redis Pub/Sub architecture." },
    { icon: Shield, title: "Enterprise Security", desc: "Complete with JWT auth, IP rate limiting, strict prompt injection filtering, and LLM budget guardrails." },
];

export default function LandingPage() {
    return (
        <div className="min-h-screen relative overflow-hidden bg-surface-900 selection:bg-brand-500/30">
            {/* ── Background Effects ── */}
            <div className="fixed inset-0 z-0 pointer-events-none">
                <div className="absolute inset-0 bg-grid-white [mask-image:linear-gradient(to_bottom,white,transparent)] opacity-10" />
                <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-brand-600/20 rounded-full blur-[120px] mix-blend-screen animate-blob" />
                <div className="absolute top-[20%] right-[-10%] w-[30%] h-[40%] bg-purple-600/20 rounded-full blur-[120px] mix-blend-screen animate-blob animation-delay-2000" />
                <div className="absolute bottom-[-20%] left-[20%] w-[50%] h-[50%] bg-blue-600/10 rounded-full blur-[120px] mix-blend-screen animate-blob animation-delay-4000" />
            </div>

            {/* ── Navbar ── */}
            <nav className="fixed top-0 inset-x-0 z-50 border-b border-white/5 bg-surface-900/50 backdrop-blur-xl">
                <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
                    <div className="flex items-center gap-2 group cursor-pointer">
                        <div className="p-1.5 rounded-lg bg-brand-500/10 border border-brand-500/20 group-hover:bg-brand-500/20 transition-colors">
                            <Sparkles className="h-5 w-5 text-brand-400" />
                        </div>
                        <span className="text-xl font-bold tracking-tight text-white">BrainWeave</span>
                    </div>
                    <div className="hidden md:flex items-center gap-8 text-sm font-medium text-slate-400">
                        <a href="#features" className="hover:text-white transition-colors">Features</a>
                        <a href="#architecture" className="hover:text-white transition-colors">Engine</a>
                        <a href="#presentation" className="hover:text-white transition-colors">Project Info</a>
                    </div>
                    <div className="flex items-center gap-3">
                        <Link href="/login" className="text-sm font-medium text-slate-300 hover:text-white transition-colors px-4 py-2">Log In</Link>
                        <Link href="/register" className="btn-brand py-2 px-5 text-sm shadow-[0_0_20px_rgba(99,102,241,0.2)] hover:shadow-[0_0_30px_rgba(99,102,241,0.4)]">
                            Deploy Agents
                        </Link>
                    </div>
                </div>
            </nav>

            {/* ── Hero ── */}
            <section className="relative pt-32 lg:pt-48 pb-20 px-6 z-10">
                <div className="max-w-7xl mx-auto grid lg:grid-cols-2 gap-12 items-center">
                    <div>
                        <motion.div initial="hidden" animate="visible" custom={0} variants={fadeUp}>
                            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-brand-500/10 text-brand-300 border border-brand-500/20 mb-6 backdrop-blur-md">
                                <span className="relative flex h-2 w-2">
                                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-400 opacity-75"></span>
                                  <span className="relative inline-flex rounded-full h-2 w-2 bg-brand-500"></span>
                                </span>
                                v1.0.0 Production Ready • Final Year Project
                            </div>
                        </motion.div>

                        <motion.h1 initial="hidden" animate="visible" custom={1} variants={fadeUp}
                            className="text-5xl lg:text-7xl font-bold tracking-tighter leading-[1.1] text-white">
                            Research at the <br />
                            <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-purple-400 to-cyan-400 animate-gradient-x">
                                Speed of AI.
                            </span>
                        </motion.h1>

                        <motion.p initial="hidden" animate="visible" custom={2} variants={fadeUp}
                            className="mt-6 text-lg lg:text-xl text-slate-400 leading-relaxed max-w-lg">
                            An autonomous multi-agent orchestration platform. Provide a goal, and 7 specialized AIs will plan, scrape, analyze data, write Python code, and generate comprehensive reports.
                        </motion.p>

                        <motion.div initial="hidden" animate="visible" custom={3} variants={fadeUp}
                            className="mt-10 flex flex-col sm:flex-row gap-4">
                            <Link href="/register" className="btn-brand text-base flex items-center justify-center gap-2 group">
                                Enter Dashboard 
                                <ArrowRight className="h-4 w-4 group-hover:translate-x-1 transition-transform" />
                            </Link>
                            <a href="#architecture" className="btn-ghost flex items-center justify-center gap-2">
                                View Architecture
                            </a>
                        </motion.div>
                    </div>

                    {/* Hero Mockup */}
                    <motion.div initial="hidden" animate="visible" custom={2} variants={fadeUp} className="relative hidden lg:block perspective-1000">
                        <div className="relative rounded-2xl border border-white/10 bg-slate-900/80 backdrop-blur-xl shadow-2xl overflow-hidden transform rotate-y-[-10deg] rotate-x-[5deg] transition-transform duration-700 hover:rotate-y-0 hover:rotate-x-0">
                            <div className="flex items-center gap-2 px-4 py-3 border-b border-white/5 bg-slate-900">
                                <div className="flex gap-1.5">
                                    <div className="w-3 h-3 rounded-full bg-red-500/80" />
                                    <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
                                    <div className="w-3 h-3 rounded-full bg-emerald-500/80" />
                                </div>
                                <div className="mx-auto text-xs text-slate-500 font-mono">arc-agent-nexus</div>
                            </div>
                            <div className="p-6 font-mono text-sm space-y-4">
                                <div className="flex gap-4 items-start animate-fade-in" style={{animationDelay: "0.5s", animationFillMode: "both"}}>
                                    <span className="text-purple-400 shrink-0">[Planner]</span>
                                    <span className="text-slate-300">Generated DAG with 4 dependencies.</span>
                                </div>
                                <div className="flex gap-4 items-start animate-fade-in" style={{animationDelay: "1.5s", animationFillMode: "both"}}>
                                    <span className="text-sky-400 shrink-0">[Research]</span>
                                    <span className="text-slate-300">Scraping IEEE Xplore: "Quantum entanglement..." <br/><span className="text-emerald-400 text-xs">✓ Extracted 4,209 tokens</span></span>
                                </div>
                                <div className="flex gap-4 items-start animate-fade-in" style={{animationDelay: "2.5s", animationFillMode: "both"}}>
                                    <span className="text-orange-400 shrink-0">[Code]</span>
                                    <span className="text-slate-300">Executing sandbox script: <span className="text-blue-300">data_analysis.py</span> <br/><span className="text-slate-500 text-xs">import pandas as pd...</span></span>
                                </div>
                                <div className="flex gap-4 items-start animate-fade-in" style={{animationDelay: "3.5s", animationFillMode: "both"}}>
                                    <span className="text-rose-400 shrink-0">[Critic]</span>
                                    <span className="text-slate-300">Evaluating output. Confidence Score: <span className="text-brand-400">94.2%</span></span>
                                </div>
                                <div className="flex gap-4 items-center mt-6 animate-pulse-glow w-fit px-3 py-1 rounded bg-brand-500/20 border border-brand-500/30">
                                    <div className="w-2 h-2 rounded-full bg-brand-400 animate-pulse" />
                                    <span className="text-brand-300 text-xs font-semibold">Report Generating...</span>
                                </div>
                            </div>
                        </div>
                    </motion.div>
                </div>
            </section>

            {/* ── Features Grid ── */}
            <section id="features" className="py-24 px-6 z-10 relative">
                <div className="max-w-7xl mx-auto">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl md:text-5xl font-bold tracking-tight text-white mb-4">Engineered for Complexity</h2>
                        <p className="text-slate-400 text-lg max-w-2xl mx-auto">Built from the ground up to handle multi-step reasoning with strict security and transparency.</p>
                    </div>

                    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {features.map((f, i) => (
                            <motion.div key={f.title} initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-100px" }} custom={i} variants={fadeUp}
                                className="glass-card p-6 flex flex-col group overflow-hidden relative">
                                <div className="absolute inset-0 bg-gradient-to-br from-brand-500/5 to-purple-500/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                                <div className="w-12 h-12 rounded-xl bg-slate-800/80 border border-white/5 flex items-center justify-center mb-6 shadow-inner relative z-10 group-hover:scale-110 transition-transform duration-500">
                                    <f.icon className="h-6 w-6 text-brand-400" />
                                </div>
                                <h3 className="text-xl font-bold text-slate-100 mb-3 relative z-10">{f.title}</h3>
                                <p className="text-slate-400 leading-relaxed relative z-10">{f.desc}</p>
                            </motion.div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ── Architecture/Agents ── */}
            <section id="architecture" className="py-24 px-6 border-t border-white/5 bg-slate-900/50 relative z-10 overflow-hidden">
                <div className="absolute inset-0 bg-dot-white opacity-5 mask-image:radial-gradient(ellipse_at_center,white,transparent_80%)" />
                
                <div className="max-w-7xl mx-auto text-center relative z-10">
                    <h2 className="text-3xl md:text-5xl font-bold tracking-tight text-white mb-6">The NLP Copilot Architecture</h2>
                    <p className="text-slate-400 text-lg max-w-2xl mx-auto mb-16">
                        Under the hood, BrainWeave builds a Directed Acyclic Graph (DAG) for every prompt, delegating parallel tasks to domain-specific LLM agents.
                    </p>

                    <div className="glass-card p-8 md:p-12 relative overflow-hidden">
                        <div className="absolute inset-0 bg-gradient-to-r from-brand-500/5 via-transparent to-purple-500/5" />
                        <div className="flex flex-wrap items-center justify-center gap-4 md:gap-8 relative z-10">
                            {["Planner", "Search", "Data", "Code", "Critic", "Repair", "Report"].map((agent, i) => (
                                <div key={agent} className="flex items-center">
                                    <div className="flex flex-col items-center gap-3 group">
                                        <div className="w-16 h-16 rounded-2xl border border-white/10 bg-slate-800/80 shadow-lg flex items-center justify-center text-lg font-bold text-white group-hover:-translate-y-2 transition-transform duration-300">
                                            {agent[0]}
                                        </div>
                                        <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{agent}</span>
                                    </div>
                                    {i < 6 && (
                                        <div className="hidden md:flex ml-8 w-12 h-0.5 bg-gradient-to-r from-brand-500/50 to-transparent relative">
                                            <div className="absolute right-0 top-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-brand-400 glow" />
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </section>

            {/* ── CTA / Final Year Project Tag ── */}
            <section id="presentation" className="py-32 px-6 relative z-10 text-center">
                <div className="max-w-3xl mx-auto">
                    <Sparkles className="h-10 w-10 text-brand-400 mx-auto mb-6 animate-pulse" />
                    <h2 className="text-4xl lg:text-5xl font-bold text-white mb-6">Ready to see it in action?</h2>
                    <p className="text-slate-400 text-lg mb-10">
                        This platform represents a complete Final Year Project demonstrating full-stack engineering, 
                        event-driven WebSockets, sandboxed security, and applied prompt engineering.
                    </p>
                    <Link href="/register" className="btn-brand text-lg px-8 py-4 shadow-[0_0_40px_rgba(99,102,241,0.3)]">
                        Launch the Application
                    </Link>
                </div>
            </section>
        </div>
    );
}
