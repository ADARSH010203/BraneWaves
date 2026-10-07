"""Validation for Planner-generated execution DAGs."""
from __future__ import annotations

from typing import Any

ALLOWED_EXECUTABLE_STEP_TYPES = {"research", "data", "code"}


class PlanValidationError(ValueError):
    """Raised when a Planner DAG is structurally unsafe or invalid."""


def validate_plan_steps(steps: list[dict[str, Any]], max_steps: int) -> list[dict[str, Any]]:
    """Validate IDs, step types, references and acyclicity before execution."""
    if not steps:
        raise PlanValidationError("Planner produced no executable steps")
    if len(steps) > max_steps:
        raise PlanValidationError(
            f"Planner produced {len(steps)} steps, exceeding task limit of {max_steps}"
        )

    ids: list[str] = []
    for index, step in enumerate(steps):
        step_id = str(step.get("id", "")).strip()
        if not step_id:
            raise PlanValidationError(f"Planner step {index + 1} is missing a non-empty id")
        if step_id in ids:
            raise PlanValidationError(f"Planner produced duplicate step id: {step_id}")
        step_type = step.get("type")
        if step_type not in ALLOWED_EXECUTABLE_STEP_TYPES:
            raise PlanValidationError(f"Unsupported planner step type: {step_type}")
        step["id"] = step_id
        ids.append(step_id)

    id_set = set(ids)
    graph: dict[str, list[str]] = {}
    for step in steps:
        step_id = str(step["id"]).strip()
        deps = [str(dep).strip() for dep in step.get("depends_on", [])]
        if step_id in deps:
            raise PlanValidationError(f"Step {step_id} cannot depend on itself")
        missing = [dep for dep in deps if dep not in id_set]
        if missing:
            raise PlanValidationError(
                f"Step {step_id} references unknown dependencies: {', '.join(missing)}"
            )
        if len(deps) != len(set(deps)):
            raise PlanValidationError(f"Step {step_id} contains duplicate dependencies")
        step["depends_on"] = deps
        graph[step_id] = deps

    # DFS cycle detection. A dependency edge A -> B means A depends on B.
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str, path: list[str]) -> None:
        if node in visited:
            return
        if node in visiting:
            cycle_start = path.index(node) if node in path else 0
            cycle = path[cycle_start:] + [node]
            raise PlanValidationError(f"Planner DAG contains a cycle: {' -> '.join(cycle)}")
        visiting.add(node)
        path.append(node)
        for dep in graph[node]:
            visit(dep, path)
        path.pop()
        visiting.remove(node)
        visited.add(node)

    for step_id in ids:
        visit(step_id, [])

    return steps
