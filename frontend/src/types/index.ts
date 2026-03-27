/* ─── ARC Platform — TypeScript Types ──────────────────────────────── */

// ── Auth ─────────────────────────────────────────────────────────────
export interface User {
    id: string;
    email: string;
    name: string;
    role: "user" | "admin";
    plan: "free" | "pro" | "enterprise";
    usage_quota_usd: number;
    created_at: string;
    is_active: boolean;
}

export interface TokenResponse {
    access_token: string;
    refresh_token: string;
    token_type: string;
}

export interface AuthResponse {
    user: User;
    tokens: TokenResponse;
}

// ── Task ─────────────────────────────────────────────────────────────
export type TaskStatus = "pending" | "planning" | "running" | "paused" | "completed" | "failed" | "cancelled";
export type StepStatus = "pending" | "running" | "completed" | "failed" | "skipped" | "retrying";
export type StepType = "research" | "data" | "code" | "critique" | "report" | "repair";
export type AgentType = "planner" | "research" | "data" | "code" | "critic" | "report" | "repair";

export interface TaskBudget {
    max_usd: number;
    spent_usd: number;
    max_steps: number;
    steps_used: number;
}

export interface Task {
    id: string;
    user_id: string;
    title: string;
    description: string;
    status: TaskStatus;
    budget: TaskBudget;
    tags: string[];
    plan?: Record<string, unknown>;
    result_summary?: string;
    report_id?: string;
    error?: string;
    created_at: string;
    updated_at: string;
    completed_at?: string;
}

export interface TaskStep {
    id: string;
    task_id: string;
    order: number;
    step_type: StepType;
    title: string;
    description: string;
    status: StepStatus;
    depends_on: string[];
    agent_type: string;
    confidence?: number;
    retries: number;
    cost_usd: number;
    error?: string;
    started_at?: string;
    completed_at?: string;
}

export interface TaskListResponse {
    tasks: Task[];
    total: number;
    page: number;
    page_size: number;
}

// ── Report / Citation ────────────────────────────────────────────────
export interface Report {
    id: string;
    task_id: string;
    title: string;
    content: string;
    format: string;
    summary?: string;
    citation_ids: string[];
    confidence: number;
    word_count: number;
    created_at: string;
}

export interface Citation {
    id: string;
    report_id: string;
    citation_type: "web" | "paper" | "dataset" | "file" | "code";
    title: string;
    url?: string;
    authors: string[];
    excerpt?: string;
    relevance_score: number;
    verified: boolean;
    verification_note?: string;
}

export interface TaskResult {
    task_id: string;
    status: TaskStatus;
    result_summary?: string;
    report?: Report;
    citations?: Citation[];
    cost_summary?: {
        total_cost_usd: number;
        total_tokens: number;
        num_agent_runs: number;
    };
}

// ── WebSocket Events ─────────────────────────────────────────────────
export interface WSEvent {
    event: string;
    task_id: string;
    timestamp: string;
    [key: string]: unknown;
}

// ── Cost ─────────────────────────────────────────────────────────────
export interface CostEntry {
    id: string;
    task_id: string;
    agent_type: string;
    tokens_total: number;
    cost_usd: number;
    created_at: string;
}
