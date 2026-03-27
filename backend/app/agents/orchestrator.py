"""
ARC Platform — Agent Orchestrator
Task graph execution engine with dependency resolution,
parallel dispatch, loop detection, and WebSocket event emission.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Optional

from app.agents.base import BaseAgent, BudgetExceededError, MaxStepsExceededError
from app.agents.planner import PlannerAgent
from app.agents.research import ResearchAgent
from app.agents.data import DataAgent
from app.agents.code import CodeAgent
from app.agents.critic import CriticAgent
from app.agents.report import ReportAgent
from app.agents.repair import RepairAgent
from app.config import get_settings
from app.database import get_db, get_redis
from app.models.agent import AgentRunStatus, AgentType
from app.models.task import StepStatus, StepType, TaskStatus

logger = logging.getLogger("arc.orchestrator")
settings = get_settings()

# ── Agent class map ──────────────────────────────────────────────────────────
AGENT_MAP: dict[str, type[BaseAgent]] = {
    AgentType.PLANNER.value: PlannerAgent,
    AgentType.RESEARCH.value: ResearchAgent,
    AgentType.DATA.value: DataAgent,
    AgentType.CODE.value: CodeAgent,
    AgentType.CRITIC.value: CriticAgent,
    AgentType.REPORT.value: ReportAgent,
    AgentType.REPAIR.value: RepairAgent,
}

STEP_TO_AGENT: dict[str, str] = {
    StepType.RESEARCH.value: AgentType.RESEARCH.value,
    StepType.DATA.value: AgentType.DATA.value,
    StepType.CODE.value: AgentType.CODE.value,
    StepType.CRITIQUE.value: AgentType.CRITIC.value,
    StepType.REPORT.value: AgentType.REPORT.value,
    StepType.REPAIR.value: AgentType.REPAIR.value,
}


class TaskOrchestrator:
    """
    Executes a task by:
    1. Running the PlannerAgent to generate a step DAG
    2. Topologically sorting steps
    3. Executing independent steps in parallel
    4. Running CriticAgent on outputs
    5. Retrying failed steps with RepairAgent
    6. Emitting events via Redis pub/sub for WebSocket streaming
    """

    def __init__(self, task_id: str, user_id: str):
        self.task_id = task_id
        self.user_id = user_id
        self._steps_completed: set[str] = set()
        self._loop_counter: dict[str, int] = defaultdict(int)
        self._total_cost = 0.0
        self._max_loops = 3

    async def execute(self) -> dict[str, Any]:
        """Main entry point: plan → execute → report."""
        db = get_db()

        # Update task status
        await db.tasks.update_one(
            {"_id": self.task_id},
            {"$set": {"status": TaskStatus.PLANNING.value, "updated_at": datetime.now(timezone.utc)}},
        )
        await self._emit_event("task_status", {"status": "planning"})

        # ── Phase 1: Planning ────────────────────────────────────────────
        task_doc = await db.tasks.find_one({"_id": self.task_id})
        if not task_doc:
            raise ValueError(f"Task {self.task_id} not found")

        planner = PlannerAgent(
            task_id=self.task_id,
            step_id="planning",
            user_id=self.user_id,
            budget_usd=settings.MAX_AGENT_BUDGET_USD,
        )
        await planner.start_run({"title": task_doc["title"], "description": task_doc["description"]})

        try:
            plan = await planner.run({
                "title": task_doc["title"],
                "description": task_doc["description"],
            })
            await planner.complete_run(plan, confidence=plan.get("confidence", 0.8))
        except Exception as e:
            await planner.complete_run({}, status=AgentRunStatus.FAILED, error=str(e))
            await self._fail_task(str(e))
            return {"error": str(e)}

        # Save plan and create steps
        steps = plan.get("steps", [])
        await db.tasks.update_one(
            {"_id": self.task_id},
            {"$set": {"plan": plan, "status": TaskStatus.RUNNING.value, "updated_at": datetime.now(timezone.utc)}},
        )
        await self._emit_event("task_status", {"status": "running", "total_steps": len(steps)})

        # Persist steps
        step_docs = []
        for i, step in enumerate(steps):
            step_id = str(uuid.uuid4())
            step["_id"] = step_id
            step_docs.append({
                "_id": step_id,
                "task_id": self.task_id,
                "order": i,
                "step_type": step.get("type", StepType.RESEARCH.value),
                "title": step.get("title", f"Step {i+1}"),
                "description": step.get("description", ""),
                "status": StepStatus.PENDING.value,
                "depends_on": step.get("depends_on", []),
                "agent_type": STEP_TO_AGENT.get(step.get("type", ""), AgentType.RESEARCH.value),
                "input_data": step.get("input_data", {}),
                "retries": 0,
                "max_retries": settings.MAX_RETRIES_PER_STEP,
                "cost_usd": 0.0,
                "created_at": datetime.now(timezone.utc),
            })

        if step_docs:
            await db.task_steps.insert_many(step_docs)

        # ── Phase 2: Execution ───────────────────────────────────────────
        try:
            await self._execute_steps(step_docs)
        except (BudgetExceededError, MaxStepsExceededError) as e:
            await self._fail_task(str(e))
            return {"error": str(e)}
        except Exception as e:
            logger.exception("Orchestrator error for task %s", self.task_id)
            await self._fail_task(str(e))
            return {"error": str(e)}

        # ── Phase 3: Report Generation ───────────────────────────────────
        await self._generate_report()

        # ── Complete ─────────────────────────────────────────────────────
        await db.tasks.update_one(
            {"_id": self.task_id},
            {"$set": {
                "status": TaskStatus.COMPLETED.value,
                "completed_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }},
        )
        await self._emit_event("task_status", {"status": "completed"})

        return {"status": "completed", "task_id": self.task_id}

    async def _execute_steps(self, step_docs: list[dict]) -> None:
        """Execute steps respecting dependency order with parallelism."""
        db = get_db()
        step_map = {s["_id"]: s for s in step_docs}
        budget = (await db.tasks.find_one({"_id": self.task_id}))["budget"]
        max_usd = budget.get("max_usd", settings.MAX_TASK_BUDGET_USD)

        while len(self._steps_completed) < len(step_docs):
            # Check budget
            if self._total_cost >= max_usd:
                raise BudgetExceededError(f"Task budget exceeded: ${self._total_cost:.4f} >= ${max_usd:.2f}")

            # Find ready steps (all dependencies met)
            ready = []
            for s in step_docs:
                sid = s["_id"]
                if sid in self._steps_completed:
                    continue
                deps = s.get("depends_on", [])
                if all(d in self._steps_completed for d in deps):
                    ready.append(s)

            if not ready:
                # Possible cycle detection
                remaining = [s["_id"] for s in step_docs if s["_id"] not in self._steps_completed]
                raise RuntimeError(f"Dependency deadlock detected. Remaining: {remaining}")

            # Execute ready steps in parallel
            tasks = [self._execute_single_step(s) for s in ready]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for s, result in zip(ready, results):
                sid = s["_id"]
                if isinstance(result, Exception):
                    logger.error("Step %s failed: %s", sid, result)
                    # Attempt repair
                    repaired = await self._attempt_repair(s, str(result))
                    if not repaired:
                        await db.task_steps.update_one(
                            {"_id": sid},
                            {"$set": {"status": StepStatus.FAILED.value, "error": str(result)}},
                        )
                self._steps_completed.add(sid)

    async def _execute_single_step(self, step: dict) -> dict[str, Any]:
        """Execute a single step with the appropriate agent."""
        db = get_db()
        sid = step["_id"]
        agent_type = step.get("agent_type", AgentType.RESEARCH.value)

        # Loop detection
        self._loop_counter[sid] += 1
        if self._loop_counter[sid] > self._max_loops:
            raise RuntimeError(f"Loop detected: step {sid} executed {self._loop_counter[sid]} times")

        await db.task_steps.update_one(
            {"_id": sid},
            {"$set": {"status": StepStatus.RUNNING.value, "started_at": datetime.now(timezone.utc)}},
        )
        await self._emit_event("step_status", {"step_id": sid, "status": "running", "agent_type": agent_type})

        # Instantiate agent
        agent_cls = AGENT_MAP.get(agent_type)
        if not agent_cls:
            raise ValueError(f"Unknown agent type: {agent_type}")

        # Gather outputs from dependency steps
        dep_outputs = {}
        if step.get("depends_on"):
            for dep_id in step["depends_on"]:
                dep_step = await db.task_steps.find_one({"_id": dep_id})
                if dep_step and dep_step.get("output_data"):
                    dep_outputs[dep_id] = dep_step["output_data"]

        input_data = {
            **(step.get("input_data") or {}),
            "step_title": step.get("title", ""),
            "step_description": step.get("description", ""),
            "dependency_outputs": dep_outputs,
            "task_id": self.task_id,
        }

        agent = agent_cls(
            task_id=self.task_id,
            step_id=sid,
            user_id=self.user_id,
            budget_usd=settings.MAX_AGENT_BUDGET_USD,
        )
        await agent.start_run(input_data)

        try:
            output = await agent.run(input_data)
            confidence = output.get("confidence", 0.5)

            # Run critic on output
            if agent_type != AgentType.CRITIC.value and agent_type != AgentType.REPAIR.value:
                critic_result = await self._run_critic(sid, output)
                confidence = critic_result.get("confidence", confidence)
                output["critic_feedback"] = critic_result

            await agent.complete_run(output, confidence=confidence)
            self._total_cost += agent._total_cost

            await db.task_steps.update_one(
                {"_id": sid},
                {"$set": {
                    "status": StepStatus.COMPLETED.value,
                    "output_data": output,
                    "confidence": confidence,
                    "cost_usd": agent._total_cost,
                    "completed_at": datetime.now(timezone.utc),
                }},
            )
            await self._emit_event("step_status", {
                "step_id": sid,
                "status": "completed",
                "confidence": confidence,
                "cost_usd": agent._total_cost,
            })

            return output

        except Exception as e:
            await agent.complete_run({}, status=AgentRunStatus.FAILED, error=str(e))
            raise

    async def _run_critic(self, step_id: str, output: dict[str, Any]) -> dict[str, Any]:
        """Run CriticAgent to validate step output."""
        critic = CriticAgent(
            task_id=self.task_id,
            step_id=step_id,
            user_id=self.user_id,
            budget_usd=settings.MAX_AGENT_BUDGET_USD * 0.3,
        )
        await critic.start_run({"output_to_review": output})
        try:
            result = await critic.run({"output_to_review": output})
            await critic.complete_run(result, confidence=result.get("confidence", 0.5))
            self._total_cost += critic._total_cost
            return result
        except Exception as e:
            await critic.complete_run({}, status=AgentRunStatus.FAILED, error=str(e))
            return {"confidence": 0.5, "feedback": f"Critic failed: {e}"}

    async def _attempt_repair(self, step: dict, error: str) -> bool:
        """Attempt to repair a failed step using RepairAgent."""
        db = get_db()
        sid = step["_id"]
        retries = step.get("retries", 0)

        if retries >= settings.MAX_RETRIES_PER_STEP:
            return False

        await db.task_steps.update_one(
            {"_id": sid},
            {"$set": {"status": StepStatus.RETRYING.value, "retries": retries + 1}},
        )
        await self._emit_event("step_status", {"step_id": sid, "status": "retrying", "retry": retries + 1})

        repair = RepairAgent(
            task_id=self.task_id,
            step_id=sid,
            user_id=self.user_id,
            budget_usd=settings.MAX_AGENT_BUDGET_USD * 0.5,
        )
        await repair.start_run({"error": error, "step": step})
        try:
            result = await repair.run({"error": error, "step": step})
            await repair.complete_run(result)
            self._total_cost += repair._total_cost

            # Update step with repaired output
            await db.task_steps.update_one(
                {"_id": sid},
                {"$set": {
                    "status": StepStatus.COMPLETED.value,
                    "output_data": result,
                    "completed_at": datetime.now(timezone.utc),
                }},
            )
            return True
        except Exception as e:
            await repair.complete_run({}, status=AgentRunStatus.FAILED, error=str(e))
            return False

    async def _generate_report(self) -> None:
        """Generate final report from all step outputs."""
        db = get_db()

        # Gather all completed step outputs
        steps = await db.task_steps.find(
            {"task_id": self.task_id, "status": StepStatus.COMPLETED.value}
        ).to_list(length=100)

        outputs = {s["_id"]: s.get("output_data", {}) for s in steps}

        report_agent = ReportAgent(
            task_id=self.task_id,
            step_id="report",
            user_id=self.user_id,
            budget_usd=settings.MAX_AGENT_BUDGET_USD,
        )
        await report_agent.start_run({"step_outputs": outputs})
        try:
            report = await report_agent.run({"step_outputs": outputs, "task_id": self.task_id})
            await report_agent.complete_run(report, confidence=report.get("confidence", 0.7))
            self._total_cost += report_agent._total_cost

            # Save report
            report_id = str(uuid.uuid4())
            task_doc = await db.tasks.find_one({"_id": self.task_id})
            report_doc = {
                "_id": report_id,
                "task_id": self.task_id,
                "user_id": self.user_id,
                "title": report.get("title", task_doc.get("title", "Research Report")),
                "content": report.get("content", ""),
                "format": "markdown",
                "summary": report.get("summary", ""),
                "sections": report.get("sections", []),
                "citation_ids": report.get("citation_ids", []),
                "confidence": report.get("confidence", 0.7),
                "word_count": len(report.get("content", "").split()),
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
            await db.reports.insert_one(report_doc)

            await db.tasks.update_one(
                {"_id": self.task_id},
                {"$set": {"report_id": report_id, "result_summary": report.get("summary", "")}},
            )
            await self._emit_event("report_generated", {"report_id": report_id})

        except Exception as e:
            await report_agent.complete_run({}, status=AgentRunStatus.FAILED, error=str(e))
            logger.error("Report generation failed for task %s: %s", self.task_id, e)

    async def _fail_task(self, error: str) -> None:
        """Mark task as failed."""
        db = get_db()
        await db.tasks.update_one(
            {"_id": self.task_id},
            {"$set": {
                "status": TaskStatus.FAILED.value,
                "error": error,
                "updated_at": datetime.now(timezone.utc),
            }},
        )
        await self._emit_event("task_status", {"status": "failed", "error": error})

    async def _emit_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish event to Redis pub/sub for WebSocket streaming."""
        try:
            redis = get_redis()
            import json
            payload = json.dumps({
                "event": event_type,
                "task_id": self.task_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **data,
            })
            await redis.publish(f"task:{self.task_id}", payload)
        except Exception as e:
            logger.warning("Failed to emit event %s: %s", event_type, e)
