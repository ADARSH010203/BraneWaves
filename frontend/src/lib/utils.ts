/* ─── ARC Platform — Utilities ────────────────────────────────────── */
import { clsx, type ClassValue } from "clsx";

export function cn(...inputs: ClassValue[]): string {
    return clsx(inputs);
}

export function formatDate(date: string): string {
    return new Date(date).toLocaleDateString("en-US", {
        year: "numeric", month: "short", day: "numeric",
        hour: "2-digit", minute: "2-digit",
    });
}

export function formatCost(usd: number): string {
    return `$${usd.toFixed(4)}`;
}

export function formatTokens(tokens: number): string {
    if (tokens >= 1_000_000) return `${(tokens / 1_000_000).toFixed(1)}M`;
    if (tokens >= 1_000) return `${(tokens / 1_000).toFixed(1)}K`;
    return String(tokens);
}

export function truncate(str: string, length: number): string {
    return str.length > length ? str.slice(0, length) + "…" : str;
}

export function getStatusColor(status: string): string {
    const map: Record<string, string> = {
        pending: "chip-pending",
        planning: "chip-running",
        running: "chip-running",
        completed: "chip-completed",
        failed: "chip-failed",
        cancelled: "chip-failed",
        skipped: "chip-pending",
        retrying: "chip-running",
    };
    return map[status] || "chip-pending";
}

export function getAgentBadgeClass(agentType: string): string {
    const map: Record<string, string> = {
        planner: "agent-planner",
        research: "agent-research",
        data: "agent-data",
        code: "agent-code",
        critic: "agent-critic",
        report: "agent-report",
        repair: "agent-repair",
    };
    return map[agentType] || "agent-research";
}
