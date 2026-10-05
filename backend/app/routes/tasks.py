"""
ARC Platform — Task Routes
POST /tasks, GET /tasks/{id}, GET /tasks/{id}/steps, GET /tasks/{id}/result
GET /tasks/{id}/export?format=pdf|docx, POST /tasks/{id}/cancel
"""
from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.deps import DbDep, UserDep
from app.models.task import TaskCreate, TaskListResponse, TaskResponse
from app.security.prompt_filter import check_prompt_injection, sanitize_user_input
from app.security.rate_limiter import rate_limit_by_user
from app.services.task_service import cancel_task, create_task, get_task, get_task_result, get_task_steps, list_tasks

logger = logging.getLogger("arc.routes.tasks")

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


# ── FEAT-01: Report Export ───────────────────────────────────────────────────
@router.get("/{task_id}/export")
async def export_report(
    task_id: str,
    db: DbDep,
    user: UserDep,
    format: Literal["pdf", "docx"] = Query(default="pdf", description="Export format: pdf or docx"),
):
    """Export the task's final report as PDF or DOCX."""
    # Verify task exists and belongs to user
    task = await db.tasks.find_one({"_id": task_id, "user_id": user["_id"]})
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if task["status"] != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Report export is only available for completed tasks",
        )

    if not task.get("report_id"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No report generated for this task",
        )

    # Fetch report
    report = await db.reports.find_one({"_id": task["report_id"]})
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report document not found",
        )

    # Fetch citations
    citations = await db.citations.find(
        {"report_id": task["report_id"]}
    ).to_list(length=200)

    # Generate export
    from app.services.export_service import ExportService

    safe_title = "".join(c for c in task.get("title", "report") if c.isalnum() or c in " _-").strip()
    safe_title = safe_title[:60] or "report"

    try:
        if format == "pdf":
            buffer = ExportService.generate_pdf(report, citations, task)
            media_type = "application/pdf"
            filename = f"{safe_title}.pdf"
        else:
            buffer = ExportService.generate_docx(report, citations, task)
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            filename = f"{safe_title}.docx"
    except Exception as e:
        logger.exception("Export generation failed for task %s: %s", task_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate {format.upper()} export",
        )

    return StreamingResponse(
        buffer,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── FEAT-02: Task Cancellation ───────────────────────────────────────────────
@router.post("/{task_id}/cancel")
async def cancel_task_endpoint(task_id: str, db: DbDep, user: UserDep):
    """Cancel a running or planning task."""
    success, message = await cancel_task(db, task_id, user["_id"])
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )
    return {"success": True, "message": message}


# ── FEAT-07: Report Follow-up Chat ───────────────────────────────────────────
from pydantic import BaseModel as PydanticBaseModel


class ChatRequest(PydanticBaseModel):
    message: str


@router.post("/{task_id}/chat")
async def chat_with_report(task_id: str, body: ChatRequest, db: DbDep, user: UserDep):
    """Chat with a completed report — uses the report content as context for Groq LLM."""
    # Validate task belongs to user and has a report
    task = await db.tasks.find_one({"_id": task_id, "user_id": user["_id"]})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if not task.get("report_id"):
        raise HTTPException(status_code=400, detail="No report available for this task yet")

    report = await db.reports.find_one({"_id": task["report_id"]})
    if not report:
        raise HTTPException(status_code=404, detail="Report document not found")

    # Fetch citations for richer context
    citations = await db.citations.find({"report_id": task["report_id"]}).to_list(length=50)
    citation_text = ""
    if citations:
        citation_text = "\n\nSources used:\n" + "\n".join(
            f"- {c.get('title', 'Unknown')} ({c.get('url', 'N/A')})" for c in citations
        )

    report_content = report.get("content", "")[:8000]
    report_summary = report.get("summary", "")

    # Build system prompt with report context
    system_prompt = f"""You are an AI research assistant for the ARC Platform. You have produced the following research report and must answer follow-up questions about it accurately and helpfully.

Report Title: {report.get('title', task.get('title', 'Research Report'))}

Report Summary: {report_summary}

Full Report Content:
{report_content}
{citation_text}

Instructions:
- Answer questions based on the report content above
- If the user asks about something not covered in the report, say so honestly
- Be concise but thorough
- Reference specific findings from the report when relevant
- If asked for recommendations, base them on the report's data and conclusions"""

    try:
        from groq import AsyncGroq
        from app.config import get_settings
        settings = get_settings()

        client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": body.message},
            ],
            temperature=0.3,
            max_tokens=2048,
        )

        reply = response.choices[0].message.content or "I couldn't generate a response."

        # Track cost
        usage = response.usage
        if usage:
            prompt_tokens = usage.prompt_tokens or 0
            completion_tokens = usage.completion_tokens or 0
            # llama-3.3-70b pricing: $0.59/M input, $0.79/M output
            cost_usd = (prompt_tokens * 0.59 / 1_000_000) + (completion_tokens * 0.79 / 1_000_000)
            await db.usage_cost.insert_one({
                "user_id": user["_id"],
                "task_id": task_id,
                "agent_type": "chat",
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
                "cost_usd": cost_usd,
                "model": "llama-3.3-70b-versatile",
            })

        return {"reply": reply}

    except Exception as e:
        logger.exception("Report chat failed for task %s: %s", task_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate chat response",
        )
