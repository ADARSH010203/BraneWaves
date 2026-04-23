"""
ARC Brain — Force Population Script
=====================================
Run this script ONCE to scan all completed tasks in your MongoDB database
and retroactively build your ARC Brain memory graph from their reports.

Usage:
    cd c:/Users/adars/OneDrive/Desktop/BrainWeave/backend
    python scripts/populate_brain.py

This will:
1. Connect to MongoDB using your existing .env settings
2. Find all completed tasks that have a report_id
3. For each report, run MemoryAgent extraction
4. Populate memory_nodes and memory_edges collections
5. Print a summary at the end
"""
import asyncio
import os
import sys
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("arc.populate_brain")

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")


async def main():
    from app.database import connect_db, get_db
    from app.config import get_settings

    settings = get_settings()
    logger.info("🔗 Connecting to MongoDB: %s", settings.MONGO_DB_NAME)
    await connect_db()
    db = get_db()

    # 1. Find all completed tasks with a report
    tasks = await db.tasks.find(
        {"status": "completed", "report_id": {"$exists": True, "$ne": None}}
    ).to_list(length=500)

    logger.info("📋 Found %d completed tasks with reports", len(tasks))

    if not tasks:
        logger.warning("No completed tasks found. Run some tasks first, then re-run this script!")
        return

    total_nodes = 0
    total_edges = 0
    skipped = 0

    for task in tasks:
        task_id = task["_id"]
        user_id = task["user_id"]
        title = task.get("title", "Unknown")
        report_id = task.get("report_id")

        logger.info("🔍 Processing task: %s — '%s'", task_id, title)

        # Fetch the report
        report = await db.reports.find_one({"_id": report_id})
        if not report:
            logger.warning("  ⚠ Report not found for task %s, skipping", task_id)
            skipped += 1
            continue

        content = report.get("content", "")
        summary = report.get("summary", "")

        if not content and not summary:
            logger.warning("  ⚠ Report has no content for task %s, skipping", task_id)
            skipped += 1
            continue

        # Check if we already have memory nodes for this task
        existing = await db.memory_nodes.find_one({"user_id": user_id, "task_ids": task_id})
        if existing:
            logger.info("  ✅ ARC Brain already has data for task %s, skipping", task_id)
            skipped += 1
            continue

        # Run memory extraction
        try:
            from app.agents.memory import MemoryAgent

            agent = MemoryAgent(
                task_id=task_id,
                step_id="populate_script",
                user_id=user_id,
                budget_usd=0.05,
            )
            memory_input = {
                "report_content": content,
                "report_summary": summary,
                "task_id": task_id,
            }
            await agent.start_run(memory_input)
            result = await agent.run(memory_input)
            await agent.complete_run(result)

            n = result.get("nodes_created", 0)
            e = result.get("edges_created", 0)
            total_nodes += n
            total_edges += e
            logger.info("  ✅ Added %d nodes, %d edges for task '%s'", n, e, title)

        except Exception as exc:
            import traceback
            logger.error("  ❌ Failed for task %s: %s\n%s", task_id, exc, traceback.format_exc())
            skipped += 1

    logger.info("")
    logger.info("═══════════════════════════════════════════════════")
    logger.info("  ✅ ARC Brain Population Complete!")
    logger.info("     Tasks processed : %d", len(tasks) - skipped)
    logger.info("     Tasks skipped   : %d", skipped)
    logger.info("     Nodes created   : %d", total_nodes)
    logger.info("     Edges created   : %d", total_edges)
    logger.info("═══════════════════════════════════════════════════")
    logger.info("  → Go to http://localhost:3000/dashboard/brain to see your graph!")


if __name__ == "__main__":
    asyncio.run(main())
