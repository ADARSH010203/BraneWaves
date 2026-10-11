"use client";

import { useEffect, useRef, useState } from "react";
import { Bot, Loader2, Send, User } from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Message {
    role: "user" | "assistant";
    content: string;
}

const greeting: Message = {
    role: "assistant",
    content: "Ask me anything about this report. I’ll use the report’s relevant sections and our previous messages as context.",
};

export function ReportChat({ taskId }: { taskId: string }) {
    const [messages, setMessages] = useState<Message[]>([greeting]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [historyLoading, setHistoryLoading] = useState(true);
    const bottomRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        let active = true;
        const load = async () => {
            try {
                const data = await api.getReportChat(taskId);
                if (!active) return;
                const history = (data.messages || []).map((m) => ({
                    role: m.role,
                    content: m.content,
                }));
                setMessages(history.length ? history : [greeting]);
            } catch {
                if (active) setMessages([greeting]);
            } finally {
                if (active) setHistoryLoading(false);
            }
        };
        void load();
        return () => { active = false; };
    }, [taskId]);

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
                ? "This task doesn't have a report yet."
                : error?.message || "I couldn't process that question. Please try again.";
            setMessages((prev) => [...prev, { role: "assistant", content: errorMsg }]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex flex-col h-[500px] glass-card rounded-2xl overflow-hidden border border-white/10">
            <div className="px-5 py-4 border-b border-white/10 bg-slate-900/50 backdrop-blur-sm flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-brand-500/20 flex items-center justify-center">
                    <Bot className="h-4 w-4 text-brand-400" />
                </div>
                <div>
                    <h3 className="font-bold text-white text-sm">Report Assistant</h3>
                    <p className="text-xs text-brand-400">Semantic report retrieval + conversation memory</p>
                </div>
            </div>

            <div className="flex-1 overflow-y-auto p-5 space-y-4 custom-scrollbar">
                {historyLoading ? (
                    <div className="h-full flex items-center justify-center text-slate-500 text-sm gap-2">
                        <Loader2 className="h-4 w-4 animate-spin" /> Loading conversation…
                    </div>
                ) : messages.map((msg, i) => (
                    <div key={i} className={cn("flex items-start gap-3 max-w-[85%]", msg.role === "user" ? "ml-auto flex-row-reverse" : "")}>
                        <div className={cn("w-8 h-8 rounded-full shrink-0 flex items-center justify-center", msg.role === "user" ? "bg-purple-500/20" : "bg-slate-800 border border-white/5")}>
                            {msg.role === "user" ? <User className="h-4 w-4 text-purple-400" /> : <Bot className="h-4 w-4 text-brand-400" />}
                        </div>
                        <div className={cn("p-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap", msg.role === "user" ? "bg-purple-500/20 text-purple-100 rounded-tr-sm" : "bg-slate-800/60 text-slate-300 border border-white/5 rounded-tl-sm")}>
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
                            <span className="text-xs text-slate-400">Retrieving relevant report evidence…</span>
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
                        onKeyDown={(e) => e.key === "Enter" && void handleSend()}
                        placeholder="Ask a follow-up about this report..."
                        disabled={historyLoading}
                        className="w-full bg-slate-950 border border-white/10 rounded-xl pl-4 pr-12 py-3 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-brand-500/50 focus:ring-1 focus:ring-brand-500/50 transition-all disabled:opacity-50"
                    />
                    <button
                        onClick={() => void handleSend()}
                        disabled={!input.trim() || loading || historyLoading}
                        className="absolute right-2 p-1.5 rounded-lg bg-brand-500/20 text-brand-400 hover:bg-brand-500/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                        <Send className="h-4 w-4" />
                    </button>
                </div>
            </div>
        </div>
    );
}
