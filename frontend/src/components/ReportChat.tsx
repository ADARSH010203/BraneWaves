"use client";

import { useState, useRef, useEffect } from "react";
import { Send, User, Bot, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Message {
    role: "user" | "assistant";
    content: string;
}

export function ReportChat({ taskId }: { taskId: string }) {
    const [messages, setMessages] = useState<Message[]>([
        { role: "assistant", content: "Hi! I produced this report. What would you like to know or discuss about it?" }
    ]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const bottomRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    const handleSend = async () => {
        if (!input.trim() || loading) return;

        const userMsg = input.trim();
        setInput("");
        setMessages((prev) => [...prev, { role: "user", content: userMsg }]);
        setLoading(true);

        try {
            const res = await api.chatWithReport(taskId, userMsg);
            setMessages((prev) => [...prev, { role: "assistant", content: res.reply }]);
        } catch (error: any) {
            const errorMsg = error?.message?.includes("No report")
                ? "This task doesn't have a report yet. The chat will be available once the report is generated."
                : "Sorry, I couldn't process that question. Please try again.";
            setMessages((prev) => [...prev, { role: "assistant", content: errorMsg }]);
        }

        setLoading(false);
    };

    return (
        <div className="flex flex-col h-[500px] glass-card rounded-2xl overflow-hidden border border-white/10">
            <div className="px-5 py-4 border-b border-white/10 bg-slate-900/50 backdrop-blur-sm flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-brand-500/20 flex items-center justify-center">
                    <Bot className="h-4 w-4 text-brand-400" />
                </div>
                <div>
                    <h3 className="font-bold text-white text-sm">Report Assistant</h3>
                    <p className="text-xs text-brand-400">Context: Executive Synthesis</p>
                </div>
            </div>

            <div className="flex-1 overflow-y-auto p-5 space-y-4 custom-scrollbar">
                {messages.map((msg, i) => (
                    <div key={i} className={cn("flex items-start gap-3 max-w-[85%]", msg.role === "user" ? "ml-auto flex-row-reverse" : "")}>
                        <div className={cn("w-8 h-8 rounded-full shrink-0 flex items-center justify-center", msg.role === "user" ? "bg-purple-500/20" : "bg-slate-800 border border-white/5")}>
                            {msg.role === "user" ? <User className="h-4 w-4 text-purple-400" /> : <Bot className="h-4 w-4 text-brand-400" />}
                        </div>
                        <div className={cn("p-3 rounded-2xl text-sm leading-relaxed", msg.role === "user" ? "bg-purple-500/20 text-purple-100 rounded-tr-sm" : "bg-slate-800/60 text-slate-300 border border-white/5 rounded-tl-sm")}>
                            {msg.content}
                        </div>
                    </div>
                ))}
                {loading && (
                    <div className="flex items-start gap-3 max-w-[85%]">
                        <div className="w-8 h-8 rounded-full shrink-0 flex items-center justify-center bg-slate-800 border border-white/5">
                            <Bot className="h-4 w-4 text-brand-400" />
                        </div>
                        <div className="p-3 rounded-2xl bg-slate-800/60 border border-white/5 rounded-tl-sm flex items-center gap-2">
                            <Loader2 className="h-4 w-4 text-brand-400 animate-spin" />
                            <span className="text-xs text-slate-400">Thinking...</span>
                        </div>
                    </div>
                )}
                <div ref={bottomRef} />
            </div>

            <div className="p-4 bg-slate-900/50 backdrop-blur-sm border-t border-white/10">
                <div className="relative flex items-center">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && handleSend()}
                        placeholder="Ask about this report..."
                        className="w-full bg-slate-950 border border-white/10 rounded-xl pl-4 pr-12 py-3 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-brand-500/50 focus:ring-1 focus:ring-brand-500/50 transition-all"
                    />
                    <button
                        onClick={handleSend}
                        disabled={!input.trim() || loading}
                        className="absolute right-2 p-1.5 rounded-lg bg-brand-500/20 text-brand-400 hover:bg-brand-500/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                        <Send className="h-4 w-4" />
                    </button>
                </div>
            </div>
        </div>
    );
}
