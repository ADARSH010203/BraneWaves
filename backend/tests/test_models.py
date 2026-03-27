"""Tests for Pydantic models — validation, defaults, serialization."""
import pytest
from datetime import datetime, timezone
from app.models.user import UserCreate, UserResponse
from app.models.task import TaskCreate, TaskBudget, TaskStatus
from app.models.agent import AgentRunDoc
from app.models.cost import UsageCostDoc


class TestUserModels:
    def test_user_create_validation(self):
        user = UserCreate(email="test@example.com", password="12345678", name="Test")
        assert user.email == "test@example.com"
        assert user.name == "Test"

    def test_user_create_invalid_email(self):
        with pytest.raises(Exception):
            UserCreate(email="invalid", password="12345678", name="Test")


class TestTaskModels:
    def test_task_create(self):
        task = TaskCreate(title="Research AI", description="Study LLMs", tags=["ai"])
        assert task.title == "Research AI"
        assert task.tags == ["ai"]

    def test_task_budget_defaults(self):
        budget = TaskBudget()
        assert budget.max_usd > 0
        assert budget.spent_usd == 0.0

    def test_task_status_enum(self):
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.COMPLETED.value == "completed"


class TestCostModels:
    def test_usage_cost_doc(self):
        doc = UsageCostDoc(
            _id="cost1", task_id="t1", run_id="r1", agent_type="research",
            model_used="llama-3.3-70b-versatile", tokens_prompt=100,
            tokens_completion=50, tokens_total=150, cost_usd=0.003,
            user_id="u1",
        )
        assert doc.tokens_total == 150
        assert doc.cost_usd == 0.003
