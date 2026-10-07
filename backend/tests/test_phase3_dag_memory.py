"""Regression tests for Phase 3 DAG validation and research memory."""
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.models.agent_outputs import StepDefinition
from app.services.plan_validation import PlanValidationError, validate_plan_steps


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
