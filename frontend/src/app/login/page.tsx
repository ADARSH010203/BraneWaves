/* ─── ARC Platform — Premium Login Page ───────────────────────────────────── */
"use client";
import { useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { useAuth } from "@/hooks/useAuth";
import { Sparkles, LogIn, AlertCircle, Eye, EyeOff, Brain, Shield, Zap } from "lucide-react";

export default function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
    } catch (err: any) {
      setError(err.message || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex relative overflow-hidden bg-surface-900">
      {/* Background Effects */}
      <div className="fixed inset-0 z-0 pointer-events-none">
        <div className="absolute inset-0 bg-grid-white opacity-[0.02]" />
        <div className="absolute top-[-20%] right-[-10%] w-[50%] h-[60%] bg-brand-600/15 rounded-full blur-[120px] animate-blob" />
        <div className="absolute bottom-[-20%] left-[-10%] w-[40%] h-[50%] bg-purple-600/10 rounded-full blur-[120px] animate-blob" style={{animationDelay: "2s"}} />
      </div>

      {/* Left Panel — Branding */}
      <div className="hidden lg:flex flex-col justify-center w-1/2 px-16 relative z-10">
        <motion.div initial={{opacity:0, x:-30}} animate={{opacity:1, x:0}} transition={{duration:0.8}}>
          <Link href="/" className="inline-flex items-center gap-3 mb-12 group">
            <div className="p-2 rounded-xl bg-brand-500/10 border border-brand-500/20 group-hover:bg-brand-500/20 transition-colors">
              <Sparkles className="h-7 w-7 text-brand-400" />
            </div>
            <span className="text-3xl font-black tracking-tight text-white">BrainWeave</span>
          </Link>

          <h2 className="text-4xl font-black text-white tracking-tight leading-tight mb-6">
            Your AI Research<br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-purple-400 to-cyan-400">
              Command Center.
            </span>
          </h2>
          <p className="text-slate-400 text-lg leading-relaxed mb-12 max-w-md">
            Orchestrate 7 autonomous AI agents to plan, research, analyze, code, and deliver comprehensive reports.
          </p>

          <div className="space-y-6">
            {[
              { icon: Brain, title: "Multi-Agent Orchestration", desc: "7 specialized agents working in parallel" },
              { icon: Shield, title: "Enterprise Security", desc: "JWT auth, prompt filtering, sandboxed execution" },
              { icon: Zap, title: "Lightning Fast", desc: "Powered by Groq LPU — 10x faster inference" },
            ].map((item, i) => (
              <motion.div key={item.title} initial={{opacity:0, y:20}} animate={{opacity:1, y:0}}
                transition={{delay: 0.3 + i * 0.15}} className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-xl bg-slate-800/80 border border-white/5 flex items-center justify-center shrink-0">
                  <item.icon className="h-5 w-5 text-brand-400" />
                </div>
                <div>
                  <h3 className="font-bold text-white text-sm">{item.title}</h3>
                  <p className="text-slate-500 text-sm">{item.desc}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>

      {/* Right Panel — Login Form */}
      <div className="flex-1 flex items-center justify-center px-6 relative z-10">
        <motion.div initial={{opacity:0, y:30}} animate={{opacity:1, y:0}} transition={{duration:0.6}}
          className="w-full max-w-md">
          
          {/* Mobile Logo */}
          <div className="text-center mb-8 lg:hidden">
            <Link href="/" className="inline-flex items-center gap-2 mb-4">
              <Sparkles className="h-8 w-8 text-brand-500" />
              <span className="text-2xl font-bold text-gradient">BrainWeave</span>
            </Link>
          </div>

          <div className="text-center lg:text-left mb-8">
            <h1 className="text-3xl font-black text-white tracking-tight">Welcome back</h1>
            <p className="text-slate-400 mt-2">Sign in to your research command center</p>
          </div>

          <form onSubmit={handleSubmit} 
            className="rounded-2xl border border-white/10 bg-slate-900/60 backdrop-blur-xl p-8 space-y-6 shadow-[0_8px_40px_rgba(0,0,0,0.3)]">
            
            {error && (
              <motion.div initial={{opacity:0, y:-10}} animate={{opacity:1, y:0}}
                className="flex items-center gap-2 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                <AlertCircle className="h-4 w-4 flex-shrink-0" />
                {error}
              </motion.div>
            )}

            <div>
              <label htmlFor="login-email" className="block text-sm font-semibold mb-2 text-slate-300">Email Address</label>
              <input id="login-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                className="input-field" placeholder="you@example.com" required autoFocus />
            </div>

            <div>
              <label htmlFor="login-password" className="block text-sm font-semibold mb-2 text-slate-300">Password</label>
              <div className="relative">
                <input id="login-password" type={showPassword ? "text" : "password"} value={password} 
                  onChange={(e) => setPassword(e.target.value)}
                  className="input-field pr-12" placeholder="••••••••" required minLength={8} />
                <button type="button" onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors">
                  {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                </button>
              </div>
            </div>

            <button type="submit" disabled={loading}
              className="btn-brand w-full flex items-center justify-center gap-2 disabled:opacity-50 py-3.5 text-base">
              {loading ? (
                <div className="h-5 w-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <><LogIn className="h-5 w-5" /> Sign In</>
              )}
            </button>

            <div className="relative">
              <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-white/5" /></div>
              <div className="relative flex justify-center text-xs">
                <span className="bg-slate-900/60 px-3 text-slate-500">or continue with</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <button type="button" onClick={() => window.location.href = "http://localhost:8000/auth/google/login"}
                className="btn-ghost py-2.5 flex items-center justify-center gap-2 text-sm border border-white/10 hover:bg-white/5 transition-colors text-slate-300">
                <svg className="w-4 h-4" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 18 19"><path fillRule="evenodd" d="M8.842 18.083a8.8 8.8 0 0 1-8.65-8.948 8.841 8.841 0 0 1 8.8-8.652h.153a8.439 8.439 0 0 1 5.8 2.312l-2.117 2.115a5.622 5.622 0 0 0-3.696-1.398 5.736 5.736 0 0 0-5.69 5.619 5.742 5.742 0 0 0 5.69 5.619 5.419 5.419 0 0 0 5.37-4.275h-5.46v-3.08h8.568a8.04 8.04 0 0 1 .15 1.83 8.354 8.354 0 0 1-8.524 8.775Z" clipRule="evenodd"/></svg>
                Google
              </button>
              <button type="button" onClick={() => window.location.href = "http://localhost:8000/auth/github/login"}
                className="btn-ghost py-2.5 flex items-center justify-center gap-2 text-sm border border-white/10 hover:bg-white/5 transition-colors text-slate-300">
                <svg className="w-5 h-5" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 24 24"><path fillRule="evenodd" d="M12.006 2a9.847 9.847 0 0 0-6.484 2.44 10.32 10.32 0 0 0-3.393 6.17 10.48 10.48 0 0 0 1.317 6.955 10.045 10.045 0 0 0 5.4 4.418c.504.095.683-.223.683-.494 0-.245-.01-1.052-.014-2.108-2.788.62-3.392-1.378-3.392-1.378-.458-1.183-1.12-1.498-1.12-1.498-.916-.64.07-.627.07-.627 1.014.073 1.547 1.062 1.547 1.062.9 1.566 2.363 1.113 2.936.851.092-.666.354-1.113.645-1.369-2.227-.26-4.569-1.135-4.569-5.045 0-1.115.39-2.029 1.03-2.747-.103-.26-.447-1.3.098-2.71 0 0 .84-.275 2.75 1.048a9.256 9.256 0 0 1 2.503-.342 9.278 9.278 0 0 1 2.503.342c1.908-1.323 2.747-1.048 2.747-1.048.547 1.41.203 2.45.1 2.71.643.718 1.03 1.632 1.03 2.747 0 3.92-2.345 4.78-4.58 5.034.364.319.688.948.688 1.912 0 1.38-.012 2.493-.012 2.833 0 .273.18.596.69.492a10.05 10.05 0 0 0 5.392-4.417 10.47 10.47 0 0 0 1.317-6.957 10.316 10.316 0 0 0-3.393-6.17A9.847 9.847 0 0 0 12.006 2Z" clipRule="evenodd"/></svg>
                GitHub
              </button>
            </div>

            <p className="text-center text-sm text-slate-400">
              Don&apos;t have an account?{" "}
              <Link href="/register" className="text-brand-400 hover:text-brand-300 font-semibold transition-colors">Create one free →</Link>
            </p>
          </form>
        </motion.div>
      </div>
    </div>
  );
}
