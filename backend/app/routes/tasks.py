"""
ARC Platform — Task Routes
POST /tasks, GET /tasks/{id}, GET /tasks/{id}/steps, GET /tasks/{id}/result
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.deps import DbDep, UserDep
from app.models.task import TaskCreate, TaskListResponse, TaskResponse
from app.security.prompt_filter import check_prompt_injection, sanitize_user_input
from app.security.rate_limiter import rate_limit_by_user
from app.services.task_service import create_task, get_task, get_task_result, get_task_steps, list_tasks

router = APIRouter()


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_new_task(data: TaskCreate, db: DbDep, user: UserDep):
    """Create a new research task."""
    await rate_limit_by_user(user["_id"])

    # Sanitise and check for prompt injection
    data.title = sanitize_user_input(data.title)
    data.description = sanitize_user_input(data.description)

    is_safe, reason = check_prompt_injection(data.description)
    if not is_safe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Input rejected: {reason}",
        )

    return await create_task(db, user["_id"], data)


@router.get("", response_model=TaskListResponse)
async def list_user_tasks(
    db: DbDep,
    user: UserDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None),
):
    """List all tasks for the authenticated user."""
    tasks, total = await list_tasks(db, user["_id"], page, page_size, status_filter)
    return TaskListResponse(tasks=tasks, total=total, page=page, page_size=page_size)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task_by_id(task_id: str, db: DbDep, user: UserDep):
    """Get a specific task by ID."""
    task = await get_task(db, task_id, user["_id"])
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@router.get("/{task_id}/steps")
async def get_steps(task_id: str, db: DbDep, user: UserDep):
    """Get all steps for a task."""
    steps = await get_task_steps(db, task_id, user["_id"])
    if steps is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return {"task_id": task_id, "steps": steps}


@router.get("/{task_id}/result")
async def get_result(task_id: str, db: DbDep, user: UserDep):
    """Get the final result/report for a task."""
    result = await get_task_result(db, task_id, user["_id"])
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return result
