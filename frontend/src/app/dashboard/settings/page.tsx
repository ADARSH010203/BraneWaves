"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, Key, Shield, Sparkles, User } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";

export default function SettingsPage() {
  const { user, updateProfile, deleteAccount } = useAuth();
  const [name, setName] = useState("");
  const [summary, setSummary] = useState<any>(null);
  const [caps, setCaps] = useState<any>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => { if (user?.name) setName(user.name); }, [user?.name]);
  useEffect(() => {
    void Promise.all([api.getDashboardSummary(), api.getCapabilities()])
      .then(([usage, capabilities]) => { setSummary(usage); setCaps(capabilities); })
      .catch((err) => console.error("Failed to load settings metadata", err));
  }, []);

  const save = async () => {
    if (!name.trim() || saving) return;
    setSaving(true);
    try {
      await updateProfile(name.trim());
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch (err: any) {
      alert(err?.message || "Failed to update profile");
    } finally { setSaving(false); }
  };

  const removeAccount = async () => {
    if (!window.confirm("Delete your ARC account permanently? This removes tasks, reports, chats, memory data, and uploaded files.")) return;
    setDeleting(true);
    try { await deleteAccount(); }
    catch (err: any) { setDeleting(false); alert(err?.message || "Failed to delete account"); }
  };

  const usagePercent = Number(summary?.usage_percent ?? 0);
  const initials = (user?.name || "U").split(" ").map((part) => part[0]).join("").toUpperCase().slice(0, 2);

  return (
    <div className="max-w-3xl mx-auto animate-fade-in space-y-6">
      <div>
        <div className="flex items-center gap-3 mb-2">
          <Sparkles className="h-6 w-6 text-brand-400" />
          <h1 className="text-3xl md:text-4xl font-black text-white">Settings</h1>
        </div>
        <p className="text-slate-400">Manage your real account and runtime configuration.</p>
      </div>

      {saved && <div className="flex items-center gap-2 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm"><CheckCircle2 className="h-5 w-5" /> Profile updated</div>}

      <div className="glass-card p-7 flex items-center gap-5">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-brand-500 to-purple-600 flex items-center justify-center text-xl font-black text-white">{initials}</div>
        <div>
          <h2 className="text-xl font-bold text-white">{user?.name || "User"}</h2>
          <p className="text-sm text-slate-400">{user?.email || ""}</p>
          <p className="text-xs text-brand-400 mt-1 uppercase">{user?.plan || "free"} · {user?.provider || "local"} login</p>
        </div>
      </div>

      <div className="glass-card p-6">
        <h2 className="font-bold text-white flex items-center gap-2 mb-5"><User className="h-5 w-5 text-brand-400" /> Profile</h2>
        <label className="block text-sm text-slate-300 mb-2">Display Name</label>
        <input className="input-field mb-4" value={name} onChange={(e) => setName(e.target.value)} maxLength={100} />
        <label className="block text-sm text-slate-300 mb-2">Email</label>
        <input className="input-field opacity-50 mb-4" value={user?.email || ""} disabled readOnly />
        <button onClick={() => void save()} disabled={saving || !name.trim()} className="btn-brand text-sm disabled:opacity-50">{saving ? "Saving..." : "Save Changes"}</button>
      </div>

      <div className="glass-card p-6">
        <h2 className="font-bold text-white flex items-center gap-2 mb-5"><Shield className="h-5 w-5 text-emerald-400" /> Plan & Usage</h2>
        <div className="flex items-center justify-between mb-3">
          <div>
            <p className="font-bold text-white capitalize">{user?.plan || "free"} Plan</p>
            <p className="text-sm text-slate-400">${Number(summary?.total_spent_usd ?? 0).toFixed(4)} used of ${Number(summary?.usage_quota_usd ?? user?.usage_quota_usd ?? 0).toFixed(2)}</p>
          </div>
          <span className="text-xs text-slate-500">Plan changes are server-managed</span>
        </div>
        <div className="h-3 rounded-full bg-slate-800 overflow-hidden"><div className="h-full bg-gradient-to-r from-emerald-500 to-cyan-500" style={{ width: `${Math.min(100, usagePercent)}%` }} /></div>
        <p className="text-xs text-slate-500 mt-2">{usagePercent.toFixed(1)}% used · ${Number(summary?.remaining_quota_usd ?? 0).toFixed(4)} remaining</p>
      </div>

      <div className="glass-card p-6">
        <h2 className="font-bold text-white flex items-center gap-2 mb-5"><Key className="h-5 w-5 text-purple-400" /> Runtime Capabilities</h2>
        <Status ok={!!caps?.llm_configured} title={caps?.llm_configured ? "Groq LLM configured" : "Groq LLM key missing"} detail={`Primary model: ${caps?.primary_model || "unknown"}`} />
        <div className="h-3" />
        <Status ok={!!caps?.python_sandbox_configured} title={caps?.python_sandbox_configured ? "Python sandbox configured" : "Python sandbox not configured"} detail={caps?.python_sandbox_configured ? "Isolated Python execution is available." : "Code/Data steps requiring Python execution will degrade until PYTHON_SANDBOX_URL is configured."} />
        <p className="text-xs text-slate-500 mt-4">Secrets remain server-side and are never returned to the browser. ARC currently uses a fixed dark interface.</p>
      </div>

      <div className="rounded-2xl border border-red-500/20 bg-red-500/5 p-6">
        <h2 className="font-bold text-red-400 flex items-center gap-2 mb-3"><AlertTriangle className="h-5 w-5" /> Danger Zone</h2>
        <p className="text-sm text-slate-400 mb-4">Permanent deletion removes tasks, reports, report chats, knowledge-base files, citations, costs, and ARC Brain data.</p>
        <button onClick={() => void removeAccount()} disabled={deleting} className="px-5 py-2.5 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm font-semibold disabled:opacity-50">{deleting ? "Deleting..." : "Delete Account Permanently"}</button>
      </div>
    </div>
  );
}

function Status({ ok, title, detail }: { ok: boolean; title: string; detail: string }) {
  return (
    <div className={`flex items-start gap-3 px-4 py-3 rounded-xl border ${ok ? "bg-emerald-500/10 border-emerald-500/20" : "bg-amber-500/10 border-amber-500/20"}`}>
      {ok ? <CheckCircle2 className="h-5 w-5 text-emerald-400 mt-0.5" /> : <AlertTriangle className="h-5 w-5 text-amber-400 mt-0.5" />}
      <div><p className={`text-sm font-bold ${ok ? "text-emerald-400" : "text-amber-300"}`}>{title}</p><p className="text-xs text-slate-400 mt-1">{detail}</p></div>
    </div>
  );
}
