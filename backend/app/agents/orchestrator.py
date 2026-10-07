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

from app.agents.base import BaseAgent, BudgetExceededError, MaxStepsExceededError, TaskCancelledException
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
from app.models.agent_outputs import (
    ResearchOutput,
    DataOutput,
    CodeOutput,
    CriticOutput,
    ReportOutput,
    PlannerOutput,
)
from app.services.plan_validation import (
    PlanValidationError,
    ensure_knowledge_grounding_step,
    validate_plan_steps,
)

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
        try:
            from app.tools.registry import register_all_tools, tool_registry
            if not tool_registry._tools:
                register_all_tools()
        except Exception:
            pass

    async def execute(self) -> dict[str, Any]:
        """Main entry point: plan → execute → report."""
        db = get_db()

        # ── Phase 1: Planning ────────────────────────────────────────────
        # Read the task before mutating its state so a task cancelled while it
        # was queued never incurs a Planner LLM call.
        task_doc = await db.tasks.find_one({"_id": self.task_id, "user_id": self.user_id})
        if not task_doc:
            raise ValueError(f"Task {self.task_id} not found")

        current_status = task_doc.get("status")
        terminal_statuses = {
            TaskStatus.COMPLETED.value,
            TaskStatus.FAILED.value,
            TaskStatus.CANCELLED.value,
        }
        if current_status in terminal_statuses:
            # A worker may crash after finishing a task but before removing the
            # Redis processing-list payload. Recovered terminal tasks are no-ops.
            await db.tasks.update_one(
                {"_id": self.task_id, "user_id": self.user_id},
                {"$set": {"budget.reserved_usd": 0.0}},
            )
            return {
                "status": current_status,
                "task_id": self.task_id,
                "error": task_doc.get("error"),
            }

        if current_status in (TaskStatus.PLANNING.value, TaskStatus.RUNNING.value):
            # Crash recovery. If a report was already persisted, preserve it and
            # finish the idempotent memory post-processing instead of generating
            # duplicate steps/report. Otherwise restart planning from a clean
            # persisted step graph while retaining actual spend.
            report_id = task_doc.get("report_id")
            report_doc = None
            if report_id:
                report_doc = await db.reports.find_one(
                    {"_id": report_id, "task_id": self.task_id, "user_id": self.user_id}
                )
            if report_doc:
                await db.tasks.update_one(
                    {"_id": self.task_id, "user_id": self.user_id},
                    {"$set": {"budget.reserved_usd": 0.0}},
                )
                await self._run_memory_for_report(report_id, report_doc)
                now = datetime.now(timezone.utc)
                await db.tasks.update_one(
                    {"_id": self.task_id, "user_id": self.user_id},
                    {"$set": {
                        "status": TaskStatus.COMPLETED.value,
                        "completed_at": now,
                        "updated_at": now,
                        "error": None,
                    }},
                )
                await self._emit_event("task_status", {
                    "status": "completed",
                    "recovered": True,
                })
                return {"status": "completed", "task_id": self.task_id, "recovered": True}

            now = datetime.now(timezone.utc)
            await db.agent_runs.update_many(
                {
                    "task_id": self.task_id,
                    "status": AgentRunStatus.RUNNING.value,
                },
                {"$set": {
                    "status": AgentRunStatus.ABORTED.value,
                    "error": "Worker recovery restarted interrupted task",
                    "completed_at": now,
                }},
            )
            await db.task_steps.delete_many({"task_id": self.task_id})
            await db.tasks.update_one(
                {"_id": self.task_id, "user_id": self.user_id},
                {"$set": {
                    "status": TaskStatus.PENDING.value,
                    "plan": None,
                    "error": None,
                    "budget.reserved_usd": 0.0,
                    "updated_at": now,
                }},
            )
            task_doc["status"] = TaskStatus.PENDING.value
            task_doc["plan"] = None
        else:
            # No LLM call can still be alive when a queued pending task starts.
            # Clear any stale reservation left by an interrupted previous process.
            await db.tasks.update_one(
                {"_id": self.task_id, "user_id": self.user_id},
                {"$set": {"budget.reserved_usd": 0.0}},
            )

        try:
            await self._check_cancellation()
        except TaskCancelledException:
            await self._cancel_task()
            return {"status": "cancelled", "task_id": self.task_id}

        planning_update = await db.tasks.update_one(
            {"_id": self.task_id, "user_id": self.user_id, "status": {"$ne": TaskStatus.CANCELLED.value}},
            {"$set": {"status": TaskStatus.PLANNING.value, "updated_at": datetime.now(timezone.utc)}},
        )
        if planning_update.modified_count != 1:
            return {"status": "cancelled", "task_id": self.task_id}
        await self._emit_event("task_status", {"status": "planning"})

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
            self._total_cost += planner._total_cost
        except Exception as e:
            await planner.complete_run({}, status=AgentRunStatus.FAILED, error=str(e))
            await self._fail_task(str(e))
            return {"error": str(e)}

        # Validate the Planner DAG before persisting or executing anything.
        # Critic, Repair, and Report are orchestrator-owned and can never appear
        # as planner-generated executable steps.
        steps = plan.get("steps", [])
        task_budget = task_doc.get("budget", {})
        max_steps = int(task_budget.get("max_steps", settings.MAX_STEPS_PER_TASK))

        knowledge_available = False
        if task_doc.get("use_knowledge_base", True):
            knowledge_query: dict[str, Any] = {
                "user_id": self.user_id,
                "task_id": "KNOWLEDGE_BASE",
                "is_indexed": True,
            }
            selected_file_ids = task_doc.get("selected_file_ids", [])
            if selected_file_ids:
                knowledge_query["_id"] = {"$in": selected_file_ids}
            knowledge_available = bool(
                await db.files.find_one(knowledge_query, {"_id": 1})
            )

        steps, grounding_injected = ensure_knowledge_grounding_step(
            steps,
            knowledge_available=knowledge_available,
        )
        plan["steps"] = steps
        plan["knowledge_grounding_injected"] = grounding_injected

        try:
            validate_plan_steps(steps, max_steps)
        except PlanValidationError as exc:
            error = str(exc)
            await self._fail_task(error)
            return {"error": error}
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
                "id": step.get("id", str(i)),
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

        # Resolve validated planner IDs to persisted UUIDs. The validator
        # guarantees every dependency exists, so nothing is silently dropped.
        idx_to_uuid = {s["id"]: s["_id"] for s in step_docs}
        for s in step_docs:
            s["depends_on"] = [idx_to_uuid[d] for d in s["depends_on"]]

        if step_docs:
            await db.task_steps.insert_many(step_docs)

        # ── Phase 2: Execution ───────────────────────────────────────────
        try:
            await self._check_cancellation()
            await self._execute_steps(step_docs)
        except TaskCancelledException:
            logger.info("Task %s cancelled by user", self.task_id)
            await self._cancel_task()
            return {"status": "cancelled", "task_id": self.task_id}
        except (BudgetExceededError, MaxStepsExceededError) as e:
            await self._fail_task(str(e))
            return {"error": str(e)}
        except Exception as e:
            logger.exception("Orchestrator error for task %s", self.task_id)
            await self._fail_task(str(e))
            return {"error": str(e)}

        # ── Phase 3: Report Generation ───────────────────────────────────
        task_budget = (await db.tasks.find_one({"_id": self.task_id})).get("budget", {})
        max_usd = float(task_budget.get("max_usd", settings.MAX_TASK_BUDGET_USD))
        if self._total_cost >= max_usd:
            await self._fail_task(
                f"Task budget exhausted before report generation: ${self._total_cost:.4f} >= ${max_usd:.2f}"
            )
            return {"error": "Task budget exhausted before report generation"}

        report_generated = await self._generate_report()
        if not report_generated:
            error = "Final report generation failed"
            await self._fail_task(error)
            return {"error": error}

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

        # Track failed and skipped steps separately from completed
        failed_step_ids: set[str] = set()
        skipped_step_ids: set[str] = set()

        while len(self._steps_completed) < len(step_docs):
            # Check for cancellation before each batch
            await self._check_cancellation()

            # Check budget
            if self._total_cost >= max_usd:
                raise BudgetExceededError(f"Task budget exceeded: ${self._total_cost:.4f} >= ${max_usd:.2f}")

            # Find ready steps (all dependencies resolved — completed, failed, or skipped)
            resolved = self._steps_completed | failed_step_ids | skipped_step_ids
            ready = []
            newly_skipped = []
            for s in step_docs:
                sid = s["_id"]
                if sid in self._steps_completed:
                    continue
                deps = s.get("depends_on", [])
                if not all(d in resolved for d in deps):
                    continue  # Not all deps resolved yet

                # Check if any dependency failed or was skipped — if so, skip this step
                bad_deps = [d for d in deps if d in failed_step_ids or d in skipped_step_ids]
                if bad_deps:
                    newly_skipped.append((s, bad_deps))
                else:
                    ready.append(s)

            # Mark newly-skipped steps (transitive propagation happens next iteration)
            for s, bad_deps in newly_skipped:
                sid = s["_id"]
                dep_names = ", ".join(bad_deps)
                skip_msg = f"Skipped: dependency step(s) failed or were skipped: {dep_names}"
                await db.task_steps.update_one(
                    {"_id": sid},
                    {"$set": {
                        "status": StepStatus.SKIPPED.value,
                        "error": skip_msg,
                        "completed_at": datetime.now(timezone.utc),
                    }},
                )
                await self._emit_event("step_status", {
                    "step_id": sid, "status": "skipped", "error": skip_msg,
                })
                skipped_step_ids.add(sid)
                self._steps_completed.add(sid)
                logger.warning("Step %s skipped: %s", sid, skip_msg)

            if not ready and not newly_skipped:
                # No progress possible — check if everything is resolved or deadlocked
                remaining = [s["_id"] for s in step_docs if s["_id"] not in self._steps_completed]
                if remaining:
                    raise RuntimeError(f"Dependency deadlock detected. Remaining: {remaining}")
                break

            if not ready:
                # Only skips happened this iteration — loop again for transitive propagation
                continue

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
                        failed_step_ids.add(sid)
                self._steps_completed.add(sid)

    async def _execute_single_step(self, step: dict) -> dict[str, Any]:
        """Execute a single step with the appropriate agent."""
        # Check for cancellation before each individual step
        await self._check_cancellation()

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

        task_scope = await db.tasks.find_one(
            {"_id": self.task_id, "user_id": self.user_id},
            {"description": 1, "use_knowledge_base": 1, "selected_file_ids": 1},
        ) or {}

        input_data = {
            **(step.get("input_data") or {}),
            "step_title": step.get("title", ""),
            "step_description": step.get("description", ""),
            "task_description": task_scope.get("description", ""),
            "dependency_outputs": dep_outputs,
            "task_id": self.task_id,
            "use_knowledge_base": task_scope.get("use_knowledge_base", True),
            "selected_file_ids": task_scope.get("selected_file_ids", []),
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

            # Every executable step receives exactly one automatic Critic pass.
            # Critic.confidence means confidence in the critique itself; output
            # quality is represented by quality_score (0-5).
            if agent_type not in (AgentType.CRITIC.value, AgentType.REPAIR.value):
                critic_result = await self._run_critic(sid, output)
                critic_verdict = critic_result.get("verdict", "pass")
                quality_score = float(critic_result.get("quality_score", 2.5))
                quality_confidence = max(0.0, min(1.0, quality_score / 5.0))
                confidence = min(float(confidence), quality_confidence)
                output["critic_feedback"] = critic_result

                if critic_verdict in ("fail", "needs_revision"):
                    logger.warning(
                        "Critic rejected step %s as '%s' (quality=%.2f/5). Attempting repair.",
                        sid, critic_verdict, quality_score,
                    )
                    await self._emit_event("step_status", {
                        "step_id": sid,
                        "status": "critic_repair",
                        "verdict": critic_verdict,
                        "quality_score": quality_score,
                    })
                    repair_error = critic_result.get("feedback") or f"Critic verdict: {critic_verdict}"
                    repaired = await self._attempt_repair(step, repair_error)
                    if not repaired:
                        raise RuntimeError(
                            f"Critic rejected step output and repair failed: {repair_error}"
                        )
                    repaired_step = await db.task_steps.find_one({"_id": sid})
                    if repaired_step and repaired_step.get("output_data"):
                        output = repaired_step["output_data"]
                        confidence = float(output.get("confidence", quality_confidence))

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

            # Cost is incremented per LLM call in BaseAgent._record_cost.
            # Here we only count the completed logical step.
            await db.tasks.update_one(
                {"_id": self.task_id},
                {"$inc": {"budget.steps_used": 1}},
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
        current_step = await db.task_steps.find_one({"_id": sid}, {"retries": 1})
        retries = int((current_step or {}).get("retries", step.get("retries", 0)))

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

            # Bug 4: Unwrap corrected_output and validate against the step's expected schema
            schema_map = {
                AgentType.RESEARCH.value: ResearchOutput,
                AgentType.DATA.value: DataOutput,
                AgentType.CODE.value: CodeOutput,
                AgentType.CRITIC.value: CriticOutput,
                AgentType.REPORT.value: ReportOutput,
                AgentType.PLANNER.value: PlannerOutput,
            }
            schema_cls = schema_map.get(step.get("agent_type"))
            
            final_output = result.get("corrected_output", result)
            if schema_cls and "corrected_output" in result:
                import json
                try:
                    parsed = await repair.parse_and_validate(json.dumps(result["corrected_output"]), schema_cls)
                    final_output = parsed.model_dump()
                except Exception as e:
                    logger.warning(f"Failed to parse repaired output with parse_and_validate: {e}, falling back to raw.")

            # Update step with repaired output
            await db.task_steps.update_one(
                {"_id": sid},
                {"$set": {
                    "status": StepStatus.COMPLETED.value,
                    "output_data": final_output,
                    "completed_at": datetime.now(timezone.utc),
                }},
            )
            return True
        except Exception as e:
            await repair.complete_run({}, status=AgentRunStatus.FAILED, error=str(e))
            return False

    async def _generate_report(self) -> bool:
        """Generate and persist the final report. Return True only on success."""
        db = get_db()

        # Gather all completed step outputs
        steps = await db.task_steps.find(
            {"task_id": self.task_id, "status": StepStatus.COMPLETED.value}
        ).to_list(length=100)

        outputs = {s["_id"]: s.get("output_data", {}) for s in steps}

        # Gather failed/skipped steps so the report can note gaps honestly
        failed_steps = await db.task_steps.find(
            {"task_id": self.task_id, "status": {"$in": [StepStatus.FAILED.value, StepStatus.SKIPPED.value]}}
        ).to_list(length=100)
        failed_info = [
            {"title": s.get("title", ""), "status": s.get("status", ""), "error": s.get("error", "")}
            for s in failed_steps
        ]

        report_id = str(uuid.uuid4())
        report_agent = ReportAgent(
            task_id=self.task_id,
            step_id="report",
            user_id=self.user_id,
            budget_usd=settings.MAX_AGENT_BUDGET_USD,
        )
        await report_agent.start_run({"step_outputs": outputs, "failed_steps": failed_info})
        try:
            report = await report_agent.run({
                "step_outputs": outputs,
                "task_id": self.task_id,
                "failed_steps": failed_info,
                "report_id": report_id,
            })
            await report_agent.complete_run(report, confidence=report.get("confidence", 0.7))
            self._total_cost += report_agent._total_cost

            # Save report using the same ID already used for citations
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
                "verified_citation_count": report.get("verified_citation_count", 0),
                "total_citation_count": report.get("total_citation_count", 0),
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

            await self._run_memory_for_report(report_id, report_doc)
            return True

        except Exception as e:
            await report_agent.complete_run({}, status=AgentRunStatus.FAILED, error=str(e))
            logger.error("Report generation failed for task %s: %s", self.task_id, e)
            return False

    async def _run_memory_for_report(
        self,
        report_id: str,
        report: dict[str, Any],
    ) -> None:
        """Run idempotent non-critical memory extraction for a persisted report."""
        db = get_db()
        existing = await db.agent_runs.find_one(
            {
                "task_id": self.task_id,
                "step_id": "memory",
                "status": AgentRunStatus.COMPLETED.value,
            },
            {"_id": 1},
        )
        if existing:
            return

        try:
            from app.agents.memory import MemoryAgent

            memory_agent = MemoryAgent(
                task_id=self.task_id,
                step_id="memory",
                user_id=self.user_id,
                budget_usd=0.05,
            )
            memory_input = {
                "report_content": report.get("content", ""),
                "report_summary": report.get("summary", ""),
                "task_id": self.task_id,
                "report_id": report_id,
            }
            await memory_agent.start_run(memory_input)
            memory_result = await memory_agent.run(memory_input)
            await memory_agent.complete_run(memory_result)
            self._total_cost += memory_agent._total_cost
            logger.info("MemoryAgent completed: %s", memory_result)
        except Exception as exc:
            logger.exception(
                "MemoryAgent failed (non-critical) for task %s: %s",
                self.task_id,
                exc,
            )

    async def _check_cancellation(self) -> None:
        """Check Redis for cancellation flag. Raises TaskCancelledException if set."""
        try:
            redis = get_redis()
            if redis is not None:
                cancel_flag = await redis.get(f"task:{self.task_id}:cancel")
                if cancel_flag == "1":
                    raise TaskCancelledException(f"Task {self.task_id} cancelled by user")
            else:
                db = get_db()
                task = await db.tasks.find_one({"_id": self.task_id}, {"status": 1})
                if task and task.get("status") == TaskStatus.CANCELLED.value:
                    raise TaskCancelledException(f"Task {self.task_id} cancelled by user")
        except TaskCancelledException:
            raise
        except Exception as e:
            # Redis unavailable — also check MongoDB status as fallback
            db = get_db()
            task = await db.tasks.find_one({"_id": self.task_id}, {"status": 1})
            if task and task.get("status") == TaskStatus.CANCELLED.value:
                raise TaskCancelledException(f"Task {self.task_id} cancelled by user")

    async def _cancel_task(self) -> None:
        """Mark task as cancelled."""
        db = get_db()
        await db.tasks.update_one(
            {"_id": self.task_id},
            {"$set": {
                "status": TaskStatus.CANCELLED.value,
                "error": "Task cancelled by user",
                "updated_at": datetime.now(timezone.utc),
            }},
        )
        await self._emit_event("task_status", {"status": "cancelled", "message": "Task cancelled by user"})

        # Mark any pending/running steps as skipped
        await db.task_steps.update_many(
            {"task_id": self.task_id, "status": {"$in": ["pending", "running"]}},
            {"$set": {"status": "skipped"}},
        )

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
            if redis is None:
                return
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
