/* ─── ARC Platform — Premium Register Page ────────────────────────────────── */
"use client";
import { useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { useAuth } from "@/hooks/useAuth";
import { Sparkles, UserPlus, AlertCircle, Eye, EyeOff, GitBranch, FileSearch, TerminalSquare } from "lucide-react";

export default function RegisterPage() {
  const { register } = useAuth();
  const [name, setName] = useState("");
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
      await register(email, password, name);
    } catch (err: any) {
      setError(err.message || "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex relative overflow-hidden bg-surface-900">
      {/* Background Effects */}
      <div className="fixed inset-0 z-0 pointer-events-none">
        <div className="absolute inset-0 bg-dot-white opacity-[0.03]" />
        <div className="absolute top-[-10%] left-[-15%] w-[45%] h-[50%] bg-purple-600/15 rounded-full blur-[120px] animate-blob" />
        <div className="absolute bottom-[-15%] right-[-10%] w-[40%] h-[45%] bg-brand-600/10 rounded-full blur-[120px] animate-blob" style={{animationDelay: "3s"}} />
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
            Deploy Your First<br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 via-pink-400 to-orange-400">
              AI Agent Team.
            </span>
          </h2>
          <p className="text-slate-400 text-lg leading-relaxed mb-12 max-w-md">
            Create an account to access the full agent orchestration pipeline — from task planning to verified research reports.
          </p>

          <div className="space-y-6">
            {[
              { icon: GitBranch, title: "DAG-Based Workflows", desc: "Automatic parallel task decomposition" },
              { icon: FileSearch, title: "Local FAISS Vector RAG", desc: "Upload docs, search with zero-latency" },
              { icon: TerminalSquare, title: "Sandboxed Python", desc: "Execute generated code in secure isolation" },
            ].map((item, i) => (
              <motion.div key={item.title} initial={{opacity:0, y:20}} animate={{opacity:1, y:0}}
                transition={{delay: 0.3 + i * 0.15}} className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-xl bg-slate-800/80 border border-white/5 flex items-center justify-center shrink-0">
                  <item.icon className="h-5 w-5 text-purple-400" />
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

      {/* Right Panel — Register Form */}
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
            <h1 className="text-3xl font-black text-white tracking-tight">Create your account</h1>
            <p className="text-slate-400 mt-2">Start orchestrating AI research agents</p>
          </div>

          <form onSubmit={handleSubmit}
            className="rounded-2xl border border-white/10 bg-slate-900/60 backdrop-blur-xl p-8 space-y-5 shadow-[0_8px_40px_rgba(0,0,0,0.3)]">
            
            {error && (
              <motion.div initial={{opacity:0, y:-10}} animate={{opacity:1, y:0}}
                className="flex items-center gap-2 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                <AlertCircle className="h-4 w-4 flex-shrink-0" />
                {error}
              </motion.div>
            )}

            <div>
              <label htmlFor="reg-name" className="block text-sm font-semibold mb-2 text-slate-300">Full Name</label>
              <input id="reg-name" type="text" value={name} onChange={(e) => setName(e.target.value)}
                className="input-field" placeholder="John Doe" required autoFocus />
            </div>

            <div>
              <label htmlFor="reg-email" className="block text-sm font-semibold mb-2 text-slate-300">Email Address</label>
              <input id="reg-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                className="input-field" placeholder="you@example.com" required />
            </div>

            <div>
              <label htmlFor="reg-password" className="block text-sm font-semibold mb-2 text-slate-300">Password</label>
              <div className="relative">
                <input id="reg-password" type={showPassword ? "text" : "password"} value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input-field pr-12" placeholder="Min 8 characters" required minLength={8} />
                <button type="button" onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors">
                  {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                </button>
              </div>
              <p className="text-xs text-slate-500 mt-2">Must be at least 8 characters</p>
            </div>

            <button type="submit" disabled={loading}
              className="btn-brand w-full flex items-center justify-center gap-2 disabled:opacity-50 py-3.5 text-base">
              {loading ? (
                <div className="h-5 w-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <><UserPlus className="h-5 w-5" /> Create Account</>
              )}
            </button>

            <div className="relative">
              <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-white/5" /></div>
              <div className="relative flex justify-center text-xs">
                <span className="bg-slate-900/60 px-3 text-slate-500">or</span>
              </div>
            </div>

            <p className="text-center text-sm text-slate-400">
              Already have an account?{" "}
              <Link href="/login" className="text-brand-400 hover:text-brand-300 font-semibold transition-colors">Sign in →</Link>
            </p>
          </form>
        </motion.div>
      </div>
    </div>
  );
}
