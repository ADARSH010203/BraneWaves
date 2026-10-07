"""Regression tests for Phase 3 DAG validation and research memory."""
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.models.agent_outputs import StepDefinition
from app.services.plan_validation import (
    PlanValidationError,
    ensure_knowledge_grounding_step,
    validate_plan_steps,
)


def test_kb_grounding_is_injected_when_plan_has_no_root_research():
    steps = [
        {"id": "data_a", "type": "data", "depends_on": []},
        {"id": "code_b", "type": "code", "depends_on": []},
    ]
    grounded, changed = ensure_knowledge_grounding_step(
        steps,
        knowledge_available=True,
    )
    assert changed is True
    assert grounded[0]["type"] == "research"
    grounding_id = grounded[0]["id"]
    assert grounded[1]["depends_on"] == [grounding_id]
    assert grounded[2]["depends_on"] == [grounding_id]


def test_existing_root_research_becomes_grounding_gate():
    steps = [
        {"id": "research_a", "type": "research", "depends_on": []},
        {"id": "data_b", "type": "data", "depends_on": []},
        {"id": "code_c", "type": "code", "depends_on": ["data_b"]},
    ]
    grounded, changed = ensure_knowledge_grounding_step(
        steps,
        knowledge_available=True,
    )
    assert changed is True
    assert grounded[1]["depends_on"] == ["research_a"]
    assert grounded[2]["depends_on"] == ["data_b"]


def test_valid_parallel_dag_is_accepted():
    steps = [
        {"id": "research_a", "type": "research", "depends_on": []},
        {"id": "data_b", "type": "data", "depends_on": []},
        {"id": "code_c", "type": "code", "depends_on": ["research_a", "data_b"]},
    ]
    assert validate_plan_steps(steps, max_steps=10) == steps


@pytest.mark.parametrize(
    "steps, message",
    [
        (
            [
                {"id": "same", "type": "research", "depends_on": []},
                {"id": "same", "type": "data", "depends_on": []},
            ],
            "duplicate step id",
        ),
        (
            [{"id": "a", "type": "research", "depends_on": ["missing"]}],
            "unknown dependencies",
        ),
        (
            [{"id": "a", "type": "research", "depends_on": ["a"]}],
            "cannot depend on itself",
        ),
        (
            [
                {"id": "a", "type": "research", "depends_on": ["b"]},
                {"id": "b", "type": "data", "depends_on": ["a"]},
            ],
            "contains a cycle",
        ),
    ],
)
def test_invalid_dags_are_rejected(steps, message):
    with pytest.raises(PlanValidationError, match=message):
        validate_plan_steps(steps, max_steps=10)


def test_dag_validation_normalizes_ids_and_dependencies():
    steps = [
        {"id": " research_a ", "type": "research", "depends_on": []},
        {"id": "data_b", "type": "data", "depends_on": [" research_a "]},
    ]
    validate_plan_steps(steps, max_steps=10)
    assert steps[0]["id"] == "research_a"
    assert steps[1]["depends_on"] == ["research_a"]


def test_planner_schema_rejects_critic_steps():
    with pytest.raises(ValidationError):
        StepDefinition(
            id="critic_1",
            type="critique",
            title="Duplicate critic",
            description="Should be orchestrator owned",
        )


class _Cursor:
    def __init__(self, rows):
        self.rows = rows

    async def to_list(self, length=None):
        return self.rows[:length] if length else list(self.rows)


class _Collection:
    def __init__(self, rows):
        self.rows = rows

    def find(self, query, projection=None):
        rows = list(self.rows)
        user_id = query.get("user_id")
        if user_id is not None:
            rows = [r for r in rows if r.get("user_id") == user_id]
        ids = query.get("_id", {}).get("$in") if isinstance(query.get("_id"), dict) else None
        if ids is not None:
            rows = [r for r in rows if r.get("_id") in ids]
        task_ids = query.get("task_id", {}).get("$in") if isinstance(query.get("task_id"), dict) else None
        if task_ids is not None:
            rows = [r for r in rows if r.get("task_id") in task_ids]
        return _Cursor(rows)


class _MemoryDb:
    def __init__(self):
        self.memory_nodes = _Collection([
            {
                "_id": "node-1",
                "user_id": "user-1",
                "label": "Battery Safety",
                "description": "Thermal safety research",
                "embedding": [1.0, 0.0],
                "task_ids": ["task-1"],
                "report_ids": ["report-1"],
                "occurrence_count": 2,
                "node_type": "topic",
            }
        ])
        self.tasks = _Collection([
            {
                "_id": "task-1",
                "user_id": "user-1",
                "title": "Battery safety study",
                "result_summary": "Prior task summary",
                "report_id": "report-1",
            }
        ])
        self.reports = _Collection([
            {
                "_id": "report-1",
                "user_id": "user-1",
                "task_id": "task-1",
                "summary": "Validated thermal findings",
                "content": "Detailed previous findings about thermal runaway and mitigation.",
            }
        ])


@pytest.mark.asyncio
async def test_memory_search_returns_previous_report_evidence(monkeypatch):
    import app.agents.memory as memory_module

    async def fake_embedding(_text):
        return [1.0, 0.0]

    monkeypatch.setattr(memory_module, "get_db", lambda: _MemoryDb())
    monkeypatch.setattr(memory_module, "generate_embedding", fake_embedding)

    results = await memory_module.search_memory_graph(
        "user-1", "battery thermal safety", top_k=3, include_sources=True
    )

    assert len(results) == 1
    assert results[0]["label"] == "Battery Safety"
    assert results[0]["sources"][0]["task_id"] == "task-1"
    assert results[0]["sources"][0]["report_summary"] == "Validated thermal findings"
    assert "thermal runaway" in results[0]["sources"][0]["report_excerpt"]


class _TerminalTasks:
    def __init__(self):
        self.updated = None

    async def find_one(self, query, projection=None):
        return {
            "_id": "task-terminal",
            "user_id": "user-1",
            "status": "completed",
            "error": None,
        }

    async def update_one(self, query, update):
        self.updated = update
        return SimpleNamespace(modified_count=1)


class _TerminalDb:
    def __init__(self):
        self.tasks = _TerminalTasks()


@pytest.mark.asyncio
async def test_recovered_terminal_task_is_idempotent_noop(monkeypatch):
    import app.agents.orchestrator as orchestrator_module

    db = _TerminalDb()
    monkeypatch.setattr(orchestrator_module, "get_db", lambda: db)

    orchestrator = orchestrator_module.TaskOrchestrator(
        task_id="task-terminal",
        user_id="user-1",
    )
    result = await orchestrator.execute()

    assert result["status"] == "completed"
    assert db.tasks.updated["$set"]["budget.reserved_usd"] == 0.0
