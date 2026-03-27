"""
ARC Platform — BaseAgent
Abstract base class for all AI agents with token tracking,
cost guarding, retry logic, and structured LLM interaction.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Optional

from groq import AsyncGroq

from app.config import get_settings
from app.database import get_db
from app.models.agent import AgentLogDoc, AgentRunDoc, AgentRunStatus, AgentType, LogLevel
from app.models.cost import UsageCostDoc
from app.observability.metrics import Timer, inc

logger = logging.getLogger("arc.agents.base")
settings = get_settings()


class BudgetExceededError(Exception):
    """Raised when an agent exceeds its cost budget."""
    pass


class MaxStepsExceededError(Exception):
    """Raised when a task exceeds its maximum step count."""
    pass


class BaseAgent(ABC):
    """
    Abstract base class for all ARC agents.

    Provides:
    - Async LLM call with token tracking
    - Cost guard (per-agent and per-task)
    - Structured logging to MongoDB
    - Retry logic with exponential backoff
    """

    agent_type: AgentType
    system_prompt: str = ""
    max_retries: int = 3
    temperature: float = 0.3

    def __init__(
        self,
        task_id: str,
        step_id: str,
        user_id: str,
        run_id: Optional[str] = None,
        budget_usd: float = 1.0,
    ):
        self.task_id = task_id
        self.step_id = step_id
        self.user_id = user_id
        self.run_id = run_id or str(uuid.uuid4())
        self.budget_usd = budget_usd
        self._total_cost = 0.0
        self._total_tokens = 0
        self._client = AsyncGroq(api_key=settings.GROQ_API_KEY)

    # ── Abstract ─────────────────────────────────────────────────────────
    @abstractmethod
    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Execute the agent's primary task. Must be implemented by subclass."""
        ...

    # ── LLM Call ─────────────────────────────────────────────────────────
    async def call_llm(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: int = 4096,
        response_format: Optional[dict] = None,
    ) -> dict[str, Any]:
        """
        Make an async LLM call with token tracking and cost logging.
        Returns dict with 'content', 'tokens', 'cost_usd'.
        """
        self._check_budget()
        model = model or settings.GROQ_MODEL
        temp = temperature if temperature is not None else self.temperature

        # Prepend system prompt if not already present
        if self.system_prompt and (not messages or messages[0].get("role") != "system"):
            messages = [{"role": "system", "content": self.system_prompt}] + messages

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temp,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format

        with Timer(f"llm_call.{self.agent_type.value}"):
            response = await self._client.chat.completions.create(**kwargs)

        # Extract usage
        usage = response.usage
        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        total_tokens = prompt_tokens + completion_tokens

        # Estimate cost (GPT-4o pricing as default)
        cost_usd = self._estimate_cost(model, prompt_tokens, completion_tokens)

        self._total_cost += cost_usd
        self._total_tokens += total_tokens

        # Metrics
        inc("tokens.total", total_tokens)
        inc("cost.total_usd", cost_usd)

        content = response.choices[0].message.content or ""

        # Log to MongoDB
        await self._log(
            event="llm_response",
            message=f"LLM call: {total_tokens} tokens, ${cost_usd:.4f}",
            data={
                "model": model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "cost_usd": cost_usd,
            },
        )

        # Record cost entry
        await self._record_cost(model, prompt_tokens, completion_tokens, cost_usd)

        return {
            "content": content,
            "tokens": {"prompt": prompt_tokens, "completion": completion_tokens, "total": total_tokens},
            "cost_usd": cost_usd,
        }

    # ── Tool Execution ───────────────────────────────────────────────────
    async def execute_tool(self, tool_name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool from the registry."""
        from app.tools.registry import tool_registry
        result = await tool_registry.execute(tool_name, tool_input, self.user_id)

        await self._log(
            event="tool_call",
            message=f"Tool executed: {tool_name}",
            data={"tool": tool_name, "input": tool_input, "result_keys": list(result.keys())},
        )
        return result

    # ── Lifecycle ────────────────────────────────────────────────────────
    async def start_run(self, input_data: dict[str, Any]) -> None:
        """Record run start in MongoDB."""
        db = get_db()
        doc = {
            "_id": self.run_id,
            "task_id": self.task_id,
            "step_id": self.step_id,
            "agent_type": self.agent_type.value,
            "status": AgentRunStatus.RUNNING.value,
            "input_data": input_data,
            "model_used": settings.GROQ_MODEL,
            "started_at": datetime.now(timezone.utc),
            "tokens_prompt": 0,
            "tokens_completion": 0,
            "tokens_total": 0,
            "cost_usd": 0.0,
            "tools_called": [],
            "retries": 0,
        }
        await db.agent_runs.insert_one(doc)

    async def complete_run(
        self,
        output_data: dict[str, Any],
        status: AgentRunStatus = AgentRunStatus.COMPLETED,
        confidence: Optional[float] = None,
        error: Optional[str] = None,
    ) -> None:
        """Record run completion in MongoDB."""
        db = get_db()
        now = datetime.now(timezone.utc)
        update = {
            "$set": {
                "status": status.value,
                "output_data": output_data,
                "tokens_total": self._total_tokens,
                "cost_usd": self._total_cost,
                "completed_at": now,
                "confidence": confidence,
                "error": error,
            }
        }
        await db.agent_runs.update_one({"_id": self.run_id}, update)

    # ── Budget ───────────────────────────────────────────────────────────
    def _check_budget(self) -> None:
        """Raise if agent has exceeded its cost budget."""
        if self._total_cost >= self.budget_usd:
            raise BudgetExceededError(
                f"Agent {self.agent_type.value} exceeded budget: "
                f"${self._total_cost:.4f} >= ${self.budget_usd:.2f}"
            )

    @staticmethod
    def _estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Estimate USD cost based on Groq model pricing."""
        # Groq pricing per 1M tokens (as of 2024)
        pricing = {
            "llama-3.3-70b-versatile": {"prompt": 0.59, "completion": 0.79},
            "llama-3.1-70b-versatile": {"prompt": 0.59, "completion": 0.79},
            "llama-3.1-8b-instant": {"prompt": 0.05, "completion": 0.08},
            "llama3-70b-8192": {"prompt": 0.59, "completion": 0.79},
            "llama3-8b-8192": {"prompt": 0.05, "completion": 0.08},
            "mixtral-8x7b-32768": {"prompt": 0.24, "completion": 0.24},
            "gemma2-9b-it": {"prompt": 0.20, "completion": 0.20},
        }
        default_rate = {"prompt": 0.59, "completion": 0.79}
        rates = pricing.get(model, default_rate)
        cost = (prompt_tokens * rates["prompt"] + completion_tokens * rates["completion"]) / 1_000_000
        return round(cost, 6)

    # ── Logging ──────────────────────────────────────────────────────────
    async def _log(
        self,
        event: str,
        message: str,
        data: Optional[dict[str, Any]] = None,
        level: LogLevel = LogLevel.INFO,
    ) -> None:
        """Write a structured log entry to MongoDB."""
        db = get_db()
        doc = {
            "_id": str(uuid.uuid4()),
            "run_id": self.run_id,
            "task_id": self.task_id,
            "agent_type": self.agent_type.value,
            "level": level.value,
            "event": event,
            "message": message,
            "data": data,
            "timestamp": datetime.now(timezone.utc),
        }
        await db.agent_logs.insert_one(doc)

    async def _record_cost(
        self, model: str, prompt_tokens: int, completion_tokens: int, cost_usd: float
    ) -> None:
        """Write cost entry to usage_cost collection."""
        db = get_db()
        doc = {
            "_id": str(uuid.uuid4()),
            "user_id": self.user_id,
            "task_id": self.task_id,
            "step_id": self.step_id,
            "run_id": self.run_id,
            "agent_type": self.agent_type.value,
            "model_used": model,
            "tokens_prompt": prompt_tokens,
            "tokens_completion": completion_tokens,
            "tokens_total": prompt_tokens + completion_tokens,
            "cost_usd": cost_usd,
            "description": f"{self.agent_type.value} LLM call",
            "created_at": datetime.now(timezone.utc),
        }
        await db.usage_cost.insert_one(doc)

    # ── Helpers ──────────────────────────────────────────────────────────
    async def parse_json_response(self, content: str) -> dict[str, Any]:
        """Attempt to parse LLM response as JSON, with fallback."""
        try:
            # Try direct parse
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON block from markdown
            if "```json" in content:
                start = content.index("```json") + 7
                end = content.index("```", start)
                return json.loads(content[start:end].strip())
            elif "```" in content:
                start = content.index("```") + 3
                end = content.index("```", start)
                return json.loads(content[start:end].strip())
            raise
