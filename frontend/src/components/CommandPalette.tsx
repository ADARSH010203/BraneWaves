"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Command } from "cmdk";
import { Search, Terminal, FileText, Activity, LayoutDashboard, PlusCircle, Sparkles, Settings } from "lucide-react";

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((open) => !open);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  const runCommand = (command: () => void) => {
    setOpen(false);
    command();
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh] bg-black/60 backdrop-blur-sm px-4">
      <div 
        className="absolute inset-0" 
        onClick={() => setOpen(false)} 
      />
      <Command 
        className="w-full max-w-2xl bg-slate-900 border border-white/10 rounded-2xl shadow-2xl overflow-hidden relative z-10"
        onKeyDown={(e) => {
          if (e.key === "Escape") setOpen(false);
        }}
      >
        <div className="flex items-center border-b border-white/5 px-4" cmdk-input-wrapper="">
          <Search className="h-5 w-5 text-slate-400 shrink-0" />
          <Command.Input 
            autoFocus 
            placeholder="Search commands, navigate tasks, or type a prompt..." 
            className="flex-1 bg-transparent border-0 outline-none focus:ring-0 text-slate-200 placeholder:text-slate-500 py-4 px-3 text-lg"
          />
          <kbd className="hidden sm:inline-flex items-center gap-1 rounded border border-white/10 bg-slate-800 px-2 py-1 text-[10px] font-mono text-slate-400">
            ESC
          </kbd>
        </div>

        <Command.List className="max-h-[350px] overflow-y-auto custom-scrollbar p-2">
          <Command.Empty className="py-6 text-center text-sm text-slate-500">
            No results found.
          </Command.Empty>

          <Command.Group heading="Navigation" className="text-xs font-semibold text-slate-500 mb-2 px-2 py-1 uppercase tracking-wider [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:font-semibold [&_[cmdk-group-heading]]:text-slate-500 [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-wider">
            <Command.Item 
              onSelect={() => runCommand(() => router.push("/dashboard"))}
              className="flex items-center gap-3 px-3 py-2.5 rounded-xl cursor-default select-none text-sm text-slate-300 hover:text-white hover:bg-slate-800/50 aria-selected:bg-slate-800 focus:bg-slate-800/50 focus:text-white transition-colors"
            >
              <LayoutDashboard className="h-4 w-4 text-brand-400" />
              <span>Dashboard Overview</span>
            </Command.Item>
            <Command.Item 
              onSelect={() => runCommand(() => router.push("/dashboard/new"))}
              className="flex items-center gap-3 px-3 py-2.5 rounded-xl cursor-default select-none text-sm text-slate-300 hover:text-white hover:bg-slate-800/50 aria-selected:bg-slate-800 focus:bg-slate-800/50 focus:text-white transition-colors"
            >
              <PlusCircle className="h-4 w-4 text-emerald-400" />
              <span>Deploy New Task</span>
            </Command.Item>
            <Command.Item 
              onSelect={() => runCommand(() => router.push("/dashboard/knowledge-base"))}
              className="flex items-center gap-3 px-3 py-2.5 rounded-xl cursor-default select-none text-sm text-slate-300 hover:text-white hover:bg-slate-800/50 aria-selected:bg-slate-800 focus:bg-slate-800/50 focus:text-white transition-colors"
            >
              <Sparkles className="h-4 w-4 text-purple-400" />
              <span>Knowledge Base</span>
            </Command.Item>
          </Command.Group>

          <Command.Group heading="Actions" className="text-xs font-semibold text-slate-500 mb-2 px-2 py-1 uppercase tracking-wider mt-2 [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:font-semibold [&_[cmdk-group-heading]]:text-slate-500 [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-wider">
            <Command.Item 
              onSelect={() => runCommand(() => router.push("/dashboard/settings"))}
              className="flex items-center gap-3 px-3 py-2.5 rounded-xl cursor-default select-none text-sm text-slate-300 hover:text-white hover:bg-slate-800/50 aria-selected:bg-slate-800 focus:bg-slate-800/50 focus:text-white transition-colors"
            >
              <Settings className="h-4 w-4 text-slate-400" />
              <span>Settings</span>
            </Command.Item>
            <Command.Item 
              onSelect={() => runCommand(() => {
                const title = window.prompt("Quick Task: What would you like to research?");
                if(title) router.push(`/dashboard/new?title=${encodeURIComponent(title)}`);
              })}
              className="flex items-center gap-3 px-3 py-2.5 rounded-xl cursor-default select-none text-sm text-slate-300 hover:text-white hover:bg-slate-800/50 aria-selected:bg-slate-800 focus:bg-slate-800/50 focus:text-white transition-colors"
            >
              <Terminal className="h-4 w-4 text-sky-400" />
              <span>Quick Create Task...</span>
            </Command.Item>
          </Command.Group>
        </Command.List>
      </Command>
    </div>
  );
}
