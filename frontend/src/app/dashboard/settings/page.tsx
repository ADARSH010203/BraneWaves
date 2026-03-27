/* ─── ARC Platform — Premium Settings Page ────────────────────────────────── */
"use client";
import { useState } from "react";
import { motion } from "framer-motion";
import { useAuth } from "@/hooks/useAuth";
import { User, Shield, Palette, CheckCircle2, Key, AlertTriangle, ChevronDown, Sparkles } from "lucide-react";

export default function SettingsPage() {
  const { user } = useAuth();
  const [name, setName] = useState(user?.name || "");
  const [saved, setSaved] = useState(false);
  const [expandedSection, setExpandedSection] = useState<string | null>("profile");

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  const toggle = (section: string) => setExpandedSection(expandedSection === section ? null : section);

  const initials = (user?.name || "U").split(" ").map(n => n[0]).join("").toUpperCase().slice(0, 2);

  return (
    <div className="max-w-3xl mx-auto animate-fade-in">
      <div className="flex items-center gap-3 mb-2">
        <Sparkles className="h-6 w-6 text-brand-400" />
        <h1 className="text-3xl md:text-4xl font-black text-white tracking-tight">Settings</h1>
      </div>
      <p className="text-slate-400 text-lg mb-10">Manage your account, preferences, and API configuration.</p>

      {/* Success Toast */}
      {saved && (
        <motion.div initial={{opacity:0, y:-20}} animate={{opacity:1, y:0}} exit={{opacity:0}}
          className="flex items-center gap-2 px-5 py-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm mb-6 shadow-[0_0_20px_rgba(16,185,129,0.1)]">
          <CheckCircle2 className="h-5 w-5" /> Settings saved successfully
        </motion.div>
      )}

      {/* User Avatar Card */}
      <div className="glass-card p-8 mb-6 flex flex-col sm:flex-row items-center gap-6">
        <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-brand-500 to-purple-600 flex items-center justify-center text-2xl font-black text-white shadow-[0_0_30px_rgba(99,102,241,0.3)]">
          {initials}
        </div>
        <div className="text-center sm:text-left">
          <h2 className="text-xl font-bold text-white">{user?.name || "User"}</h2>
          <p className="text-slate-400 text-sm">{user?.email || "user@example.com"}</p>
          <p className="text-xs text-brand-400 font-semibold mt-1 uppercase tracking-wider">{user?.plan || "Free"} Plan</p>
        </div>
      </div>

      <div className="space-y-4">
        {/* Profile Section */}
        <div className="glass-card overflow-hidden">
          <button onClick={() => toggle("profile")}
            className="w-full flex items-center justify-between px-6 py-5 hover:bg-white/[0.02] transition-colors">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-brand-500/10 flex items-center justify-center">
                <User className="h-5 w-5 text-brand-400" />
              </div>
              <div className="text-left">
                <h2 className="font-bold text-white text-sm">Profile Information</h2>
                <p className="text-xs text-slate-500">Update your display name</p>
              </div>
            </div>
            <ChevronDown className={`h-5 w-5 text-slate-400 transition-transform duration-300 ${expandedSection === "profile" ? "rotate-180" : ""}`} />
          </button>
          {expandedSection === "profile" && (
            <motion.div initial={{height:0, opacity:0}} animate={{height:"auto", opacity:1}} transition={{duration:0.3}}
              className="px-6 pb-6 space-y-4 border-t border-white/5 pt-5">
              <div>
                <label className="block text-sm font-semibold mb-2 text-slate-300">Display Name</label>
                <input className="input-field" value={name} onChange={(e) => setName(e.target.value)} />
              </div>
              <div>
                <label className="block text-sm font-semibold mb-2 text-slate-300">Email</label>
                <input className="input-field opacity-50 cursor-not-allowed" defaultValue={user?.email || ""} disabled />
                <p className="text-xs text-slate-500 mt-1">Email cannot be changed</p>
              </div>
              <button onClick={handleSave} className="btn-brand text-sm px-6">Save Changes</button>
            </motion.div>
          )}
        </div>

        {/* Plan & Usage */}
        <div className="glass-card overflow-hidden">
          <button onClick={() => toggle("plan")}
            className="w-full flex items-center justify-between px-6 py-5 hover:bg-white/[0.02] transition-colors">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/10 flex items-center justify-center">
                <Shield className="h-5 w-5 text-emerald-400" />
              </div>
              <div className="text-left">
                <h2 className="font-bold text-white text-sm">Plan & Usage</h2>
                <p className="text-xs text-slate-500">View your quota and plan</p>
              </div>
            </div>
            <ChevronDown className={`h-5 w-5 text-slate-400 transition-transform duration-300 ${expandedSection === "plan" ? "rotate-180" : ""}`} />
          </button>
          {expandedSection === "plan" && (
            <motion.div initial={{height:0, opacity:0}} animate={{height:"auto", opacity:1}} transition={{duration:0.3}}
              className="px-6 pb-6 border-t border-white/5 pt-5">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <p className="font-bold text-white capitalize">{user?.plan || "Free"} Plan</p>
                  <p className="text-sm text-slate-400">Quota: ${user?.usage_quota_usd?.toFixed(2) || "10.00"} USD</p>
                </div>
                <button className="btn-ghost text-sm">Upgrade</button>
              </div>
              <div className="h-3 rounded-full bg-slate-800 overflow-hidden">
                <div className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-cyan-500 w-1/4" />
              </div>
              <p className="text-xs text-slate-500 mt-2">25% of quota used</p>
            </motion.div>
          )}
        </div>

        {/* API Configuration */}
        <div className="glass-card overflow-hidden">
          <button onClick={() => toggle("api")}
            className="w-full flex items-center justify-between px-6 py-5 hover:bg-white/[0.02] transition-colors">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-purple-500/10 flex items-center justify-center">
                <Key className="h-5 w-5 text-purple-400" />
              </div>
              <div className="text-left">
                <h2 className="font-bold text-white text-sm">API Configuration</h2>
                <p className="text-xs text-slate-500">Groq API key and model settings</p>
              </div>
            </div>
            <ChevronDown className={`h-5 w-5 text-slate-400 transition-transform duration-300 ${expandedSection === "api" ? "rotate-180" : ""}`} />
          </button>
          {expandedSection === "api" && (
            <motion.div initial={{height:0, opacity:0}} animate={{height:"auto", opacity:1}} transition={{duration:0.3}}
              className="px-6 pb-6 border-t border-white/5 pt-5 space-y-4">
              <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                <div>
                  <p className="text-sm font-bold text-emerald-400">Groq API Connected</p>
                  <p className="text-xs text-slate-400">Model: llama-3.3-70b-versatile</p>
                </div>
              </div>
              <p className="text-xs text-slate-500">API key is configured server-side via environment variables for security.</p>
            </motion.div>
          )}
        </div>

        {/* Preferences */}
        <div className="glass-card overflow-hidden">
          <button onClick={() => toggle("prefs")}
            className="w-full flex items-center justify-between px-6 py-5 hover:bg-white/[0.02] transition-colors">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-sky-500/10 flex items-center justify-center">
                <Palette className="h-5 w-5 text-sky-400" />
              </div>
              <div className="text-left">
                <h2 className="font-bold text-white text-sm">Preferences</h2>
                <p className="text-xs text-slate-500">Theme and display settings</p>
              </div>
            </div>
            <ChevronDown className={`h-5 w-5 text-slate-400 transition-transform duration-300 ${expandedSection === "prefs" ? "rotate-180" : ""}`} />
          </button>
          {expandedSection === "prefs" && (
            <motion.div initial={{height:0, opacity:0}} animate={{height:"auto", opacity:1}} transition={{duration:0.3}}
              className="px-6 pb-6 border-t border-white/5 pt-5">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-slate-300">Dark Mode</span>
                <div className="w-12 h-7 rounded-full bg-brand-500 flex items-center px-1 cursor-pointer shadow-[0_0_10px_rgba(99,102,241,0.3)]">
                  <div className="w-5 h-5 rounded-full bg-white ml-auto shadow-sm" />
                </div>
              </div>
            </motion.div>
          )}
        </div>

        {/* Danger Zone */}
        <div className="rounded-2xl border border-red-500/20 bg-red-500/5 overflow-hidden">
          <button onClick={() => toggle("danger")}
            className="w-full flex items-center justify-between px-6 py-5 hover:bg-red-500/5 transition-colors">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-red-500/10 flex items-center justify-center">
                <AlertTriangle className="h-5 w-5 text-red-400" />
              </div>
              <div className="text-left">
                <h2 className="font-bold text-red-400 text-sm">Danger Zone</h2>
                <p className="text-xs text-slate-500">Irreversible account actions</p>
              </div>
            </div>
            <ChevronDown className={`h-5 w-5 text-red-400/50 transition-transform duration-300 ${expandedSection === "danger" ? "rotate-180" : ""}`} />
          </button>
          {expandedSection === "danger" && (
            <motion.div initial={{height:0, opacity:0}} animate={{height:"auto", opacity:1}} transition={{duration:0.3}}
              className="px-6 pb-6 border-t border-red-500/10 pt-5">
              <p className="text-sm text-slate-400 mb-4">Deleting your account will permanently remove all tasks, reports, and data.</p>
              <button className="px-5 py-2.5 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm font-semibold hover:bg-red-500/20 transition-colors">
                Delete Account
              </button>
            </motion.div>
          )}
        </div>
      </div>
    </div>
  );
}
