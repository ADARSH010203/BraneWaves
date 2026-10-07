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
from typing import Any, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

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


class TaskCancelledException(Exception):
    """Raised when a user cancels a running task."""
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
        self._client = None

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
        tools: Optional[list[dict]] = None,
    ) -> dict[str, Any]:
        """
        Make an async LLM call with token tracking and cost logging using litellm.
        Returns dict with 'content', 'tokens', 'cost_usd'.
        """
        self._check_budget()
        temp = temperature if temperature is not None else self.temperature

        # Prepend system prompt if not already present
        if self.system_prompt and (not messages or messages[0].get("role") != "system"):
            messages = [{"role": "system", "content": self.system_prompt}] + messages

        from app.agents.llm_client import chat_completion
        from app.services.budget_service import (
            estimate_llm_reservation,
            finalize_task_budget,
            release_task_budget,
            reserve_task_budget,
        )

        db = get_db()
        reserved_usd = estimate_llm_reservation(messages, max_tokens)
        await reserve_task_budget(db, self.task_id, self.user_id, reserved_usd)

        try:
            with Timer(f"llm_call.{self.agent_type.value}"):
                response = await chat_completion(
                    messages=messages,
                    model=model,
                    temperature=temp,
                    max_tokens=max_tokens,
                    response_format=response_format,
                    tools=tools,
                )
        except Exception:
            await release_task_budget(db, self.task_id, self.user_id, reserved_usd)
            raise

        # Extract usage
        usage = response.usage
        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        total_tokens = prompt_tokens + completion_tokens

        used_model = response.model or model or settings.GROQ_MODEL
        cost_usd = self._estimate_cost(used_model, prompt_tokens, completion_tokens)
        await finalize_task_budget(db, self.task_id, self.user_id, reserved_usd, cost_usd)

        self._total_cost += cost_usd
        self._total_tokens += total_tokens

        # Metrics
        inc("tokens.total", total_tokens)
        inc("cost.total_usd", cost_usd)

        content = response.choices[0].message.content or ""
        tool_calls = response.choices[0].message.tool_calls or []

        # Log to MongoDB
        await self._log(
            event="llm_response",
            message=f"LLM call: {total_tokens} tokens, ${cost_usd:.4f}",
            data={
                "model": used_model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "cost_usd": cost_usd,
            },
        )

        # Record cost entry
        await self._record_cost(used_model, prompt_tokens, completion_tokens, cost_usd)

        return {
            "content": content,
            "tool_calls": tool_calls,
            "tokens": {"prompt": prompt_tokens, "completion": completion_tokens, "total": total_tokens},
            "cost_usd": cost_usd,
        }

    async def call_llm_streaming(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: int = 4096,
    ):
        """
        Stream LLM output token by token.
        """
        self._check_budget()
        temp = temperature if temperature is not None else self.temperature

        if self.system_prompt and (not messages or messages[0].get("role") != "system"):
            messages = [{"role": "system", "content": self.system_prompt}] + messages

        from app.agents.llm_client import stream_chat_completion
        from app.database import get_redis
        import json
        
        redis_client = get_redis()

        async for chunk in stream_chat_completion(
            messages=messages,
            model=model,
            temperature=temp,
            max_tokens=max_tokens,
        ):
            try:
                payload = json.dumps({
                    "event": "token_stream",
                    "task_id": self.task_id,
                    "step_id": self.step_id if hasattr(self, "step_id") else "report",
                    "agent_type": self.agent_type.value,
                    "chunk": chunk
                })
                await redis_client.publish(f"task:{self.task_id}", payload)
            except Exception:
                pass
            yield chunk

    # ── Tool Execution ───────────────────────────────────────────────────
    async def execute_tool(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        *,
        allowed_tools: set[str] | None = None,
        granted_scopes: set[str] | None = None,
    ) -> dict[str, Any]:
        """Execute a tool with explicit per-agent authorization."""
        from app.tools.registry import tool_registry
        result = await tool_registry.execute(
            tool_name,
            tool_input,
            self.user_id,
            allowed_tools=allowed_tools,
            granted_scopes=granted_scopes,
        )

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
        # Groq pricing per 1M tokens, verified against Groq model docs (Oct 2026).
        pricing = {
            "openai/gpt-oss-120b": {"prompt": 0.15, "completion": 0.60},
            "groq/openai/gpt-oss-120b": {"prompt": 0.15, "completion": 0.60},
            "openai/gpt-oss-20b": {"prompt": 0.075, "completion": 0.30},
            "groq/openai/gpt-oss-20b": {"prompt": 0.075, "completion": 0.30},
            "qwen/qwen3.8-27b": {"prompt": 0.80, "completion": 4.00},
            "groq/qwen/qwen3.8-27b": {"prompt": 0.80, "completion": 4.00},
        }
        default_rate = pricing["openai/gpt-oss-120b"]
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
        """Attempt to parse LLM response as JSON, with robust fallback for LaTeX math and markdown."""
        import re
        try:
            return json.loads(content, strict=False)
        except (json.JSONDecodeError, TypeError):
            pass

        # Try extracting JSON code block from markdown
        extracted = content
        if "```json" in content:
            start = content.index("```json") + 7
            end = content.find("```", start)
            extracted = content[start:end].strip() if end != -1 else content[start:].strip()
        elif "```" in content:
            start = content.index("```") + 3
            end = content.find("```", start)
            extracted = content[start:end].strip() if end != -1 else content[start:].strip()

        try:
            return json.loads(extracted, strict=False)
        except (json.JSONDecodeError, TypeError):
            pass

        # Clean unescaped backslashes in math/latex (e.g. \psi, \alpha, \frac, \text)
        cleaned = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', extracted)
        try:
            return json.loads(cleaned, strict=False)
        except (json.JSONDecodeError, TypeError):
            pass

        # If enclosed between outer curly braces
        start = extracted.find("{")
        end = extracted.rfind("}") + 1
        if start >= 0 and end > start:
            sub = extracted[start:end]
            try:
                return json.loads(sub, strict=False)
            except Exception:
                sub_cleaned = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', sub)
                return json.loads(sub_cleaned, strict=False)

        raise json.JSONDecodeError("Failed to parse JSON", content, 0)

    T = TypeVar("T", bound=BaseModel)

    async def parse_and_validate(self, content: str, schema: Type[T]) -> T:
        """Parse LLM JSON response and validate against Pydantic schema, with 1 retry on failure."""
        try:
            parsed = await self.parse_json_response(content)
            return schema.model_validate(parsed)
        except ValidationError as e:
            logger.warning("Validation error on LLM output: %s", e)
            # Retry once with a corrective prompt
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": "Please generate the output."},
                {"role": "assistant", "content": content},
                {"role": "user", "content": f"Your JSON did not match the required schema: {e.errors()}. Please resend valid JSON matching the schema precisely."}
            ]
            result = await self.call_llm(messages, response_format={"type": "json_object"})
            parsed_retry = await self.parse_json_response(result["content"])
            return schema.model_validate(parsed_retry)

    async def run_agentic_loop(self, messages: list[dict[str, str]], available_tools: list[str], max_iterations: int = 6) -> dict[str, Any]:
        """Run a ReAct loop calling tools until a final answer is returned or max iterations hit."""
        from app.tools.registry import tool_registry
        from app.agents.llm_client import extract_failed_generation

        tools_schema = []
        for t_name in available_tools:
            schema = tool_registry.build_tool_schema(t_name)
            if schema:
                tools_schema.append(schema)

        iterations = 0
        total_cost = 0.0
        total_tokens = 0
        content = ""
        
        while iterations < max_iterations:
            self._check_budget()
            
            # Call LLM
            is_last_iteration = iterations == (max_iterations - 1)
            current_tools = tools_schema if not is_last_iteration else None
            
            try:
                response = await self.call_llm(
                    messages,
                    tools=current_tools,
                )
            except Exception as e:
                # If Groq rejected a nonexistent tool call like 'json', extract from failed_generation
                extracted_json = extract_failed_generation(e)

                if extracted_json:
                    return {
                        "content": extracted_json,
                        "cost_usd": total_cost,
                        "tokens": total_tokens
                    }
                raise e
            
            total_cost += response.get("cost_usd", 0.0)
            total_tokens += response.get("tokens", {}).get("total", 0)
            
            tool_calls = response.get("tool_calls", [])
            content = response.get("content", "")
            
            if content:
                messages.append({"role": "assistant", "content": content})
            
            if tool_calls:
                # Check if any tool call is 'json' (LLM attempted to return answer as a function call)
                for tc in tool_calls:
                    if tc.function.name in ("json", "submit_answer", "final_answer"):
                        args = tc.function.arguments
                        return {
                            "content": args if isinstance(args, str) else json.dumps(args),
                            "cost_usd": total_cost,
                            "tokens": total_tokens
                        }

                tool_calls_dict = []
                for tc in tool_calls:
                    tool_calls_dict.append({
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    })
                
                if content:
                    messages[-1]["tool_calls"] = tool_calls_dict
                else:
                    messages.append({"role": "assistant", "tool_calls": tool_calls_dict})

                for tc in tool_calls:
                    t_name = tc.function.name
                    try:
                        t_args = json.loads(tc.function.arguments) if isinstance(tc.function.arguments, str) else (tc.function.arguments or {})
                    except Exception:
                        t_args = {}
                    
                    try:
                        scopes = {"basic"}
                        if "python_sandbox" in available_tools:
                            scopes.add("elevated")
                        t_result = await self.execute_tool(
                            t_name,
                            t_args,
                            allowed_tools=set(available_tools),
                            granted_scopes=scopes,
                        )
                        result_str = json.dumps(t_result)
                    except Exception as e:
                        result_str = json.dumps({"error": str(e)})
                        
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": t_name,
                        "content": result_str
                    })
                iterations += 1
            else:
                # No tool calls = final answer
                if content.strip():
                    return {
                        "content": content,
                        "cost_usd": total_cost,
                        "tokens": total_tokens
                    }
                # Empty content with no tool calls — force a synthesis below
                break
                
        # Forced final synthesis: compile user task + tool outputs into a clean prompt
        tool_findings = []
        user_prompt = ""
        for m in messages:
            if m.get("role") == "user" and not user_prompt:
                user_prompt = m.get("content", "")
            elif m.get("role") == "tool":
                tool_findings.append(f"Tool {m.get('name')}: {m.get('content')}")

        logger.info("Agentic loop finished — synthesising final answer from %d tool results", len(tool_findings))
        synthesis_messages = [
            {"role": "system", "content": self.system_prompt},
            {
                "role": "user",
                "content": f"""{user_prompt}

Data and Tool Results Gathered:
{chr(10).join(tool_findings) if tool_findings else "No external tool data was retrieved."}

Based on all the information and findings above, provide the complete, detailed final answer as valid JSON matching the required schema. Ensure all fields are fully populated with high quality content."""
            }
        ]
        try:
            synthesis = await self.call_llm(
                synthesis_messages,
                tools=None,
                response_format={"type": "json_object"},
            )
            total_cost += synthesis.get("cost_usd", 0.0)
            total_tokens += synthesis.get("tokens", {}).get("total", 0)
            content = synthesis.get("content", "")
        except Exception as e:
            extracted = extract_failed_generation(e)
            if extracted:
                content = extracted

        return {
            "content": content or "{}",
            "cost_usd": total_cost,
            "tokens": total_tokens
        }
