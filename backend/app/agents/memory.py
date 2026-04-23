"""
ARC Platform — MemoryAgent
Extracts key topics/entities from a completed report and stores them
as nodes + edges in the user's persistent memory graph.
"""
from __future__ import annotations
import uuid
import logging
from datetime import datetime, timezone
from typing import Any

import numpy as np

from app.agents.base import BaseAgent
from app.database import get_db
from app.models.agent import AgentType
from app.rag.embeddings import generate_embedding

logger = logging.getLogger("arc.agents.memory")


class MemoryAgent(BaseAgent):
    agent_type = AgentType.REPORT  # reuse existing enum, memory is post-report

    system_prompt = """You are a knowledge graph extraction agent. Given a research report,
extract the most important topics, entities, and concepts as discrete nodes.

Output a JSON object:
{
  "nodes": [
    {
      "label": "Short topic name (3 words max)",
      "type": "topic|entity|technology|concept",
      "description": "One sentence description"
    }
  ],
  "summary": "2-sentence summary of what was researched"
}

Rules:
- Extract 5-15 nodes maximum
- Labels must be concise and reusable (e.g. "Tesla", "EV Market", "Battery Tech")
- Focus on nouns and noun phrases — no verbs or sentences as labels
- Only include topics that would be useful in future research tasks"""

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        report_content = input_data.get("report_content", "")
        report_summary = input_data.get("report_summary", "")
        task_id = input_data.get("task_id", self.task_id)

        if not report_content and not report_summary:
            return {"nodes_created": 0, "edges_created": 0}

        text_to_analyze = f"{report_summary}\n\n{report_content[:4000]}"

        messages = [{
            "role": "user",
            "content": f"Extract key topics and entities from this research:\n\n{text_to_analyze}\n\nOutput as JSON."
        }]

        try:
            result = await self.call_llm(
                messages,
                model="llama-3.1-8b-instant",
                temperature=0.1,
                max_tokens=1024,
                response_format={"type": "json_object"},
            )

            extracted = await self.parse_json_response(result["content"])
        except Exception as e:
            import traceback
            print(f"\n\n[MemoryAgent Error] Failed to extract knowledge graph: {e}")
            print(traceback.format_exc())
            return {"nodes_created": 0, "edges_created": 0}
        nodes_data = extracted.get("nodes", [])

        if not nodes_data:
            return {"nodes_created": 0, "edges_created": 0}

        db = get_db()
        created_node_ids = []

        for node_data in nodes_data[:15]:
            label = node_data.get("label", "").strip()
            if not label:
                continue

            # Check if this node already exists for this user
            existing = await db.memory_nodes.find_one({
                "user_id": self.user_id,
                "label": {"$regex": f"^{label}$", "$options": "i"}
            })

            if existing:
                # Update existing node
                await db.memory_nodes.update_one(
                    {"_id": existing["_id"]},
                    {
                        "$inc": {"occurrence_count": 1},
                        "$addToSet": {"task_ids": task_id},
                        "$set": {"last_seen": datetime.now(timezone.utc)}
                    }
                )
                created_node_ids.append(existing["_id"])
            else:
                # Create new node
                try:
                    embedding = await generate_embedding(label + " " + node_data.get("description", ""))
                except Exception:
                    embedding = []

                node_id = str(uuid.uuid4())
                node_doc = {
                    "_id": node_id,
                    "user_id": self.user_id,
                    "label": label,
                    "node_type": node_data.get("type", "topic"),
                    "description": node_data.get("description", ""),
                    "embedding": embedding,
                    "task_ids": [task_id],
                    "occurrence_count": 1,
                    "last_seen": datetime.now(timezone.utc),
                    "created_at": datetime.now(timezone.utc),
                    "metadata": {},
                }
                await db.memory_nodes.insert_one(node_doc)
                created_node_ids.append(node_id)

        # Create edges between co-occurring nodes (all pairs)
        edges_created = 0
        for i in range(len(created_node_ids)):
            for j in range(i + 1, len(created_node_ids)):
                from_id, to_id = sorted([created_node_ids[i], created_node_ids[j]])
                existing_edge = await db.memory_edges.find_one({
                    "user_id": self.user_id,
                    "from_node_id": from_id,
                    "to_node_id": to_id,
                })
                if existing_edge:
                    await db.memory_edges.update_one(
                        {"_id": existing_edge["_id"]},
                        {
                            "$inc": {"co_occurrence_count": 1, "weight": 0.1},
                            "$addToSet": {"task_ids": task_id},
                            "$set": {"updated_at": datetime.now(timezone.utc)},
                        }
                    )
                else:
                    await db.memory_edges.insert_one({
                        "_id": str(uuid.uuid4()),
                        "user_id": self.user_id,
                        "from_node_id": from_id,
                        "to_node_id": to_id,
                        "weight": 1.0,
                        "co_occurrence_count": 1,
                        "task_ids": [task_id],
                        "created_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc),
                    })
                    edges_created += 1

        logger.info("MemoryAgent: %d nodes, %d edges created for task %s", len(created_node_ids), edges_created, task_id)
        return {
            "nodes_created": len(created_node_ids),
            "edges_created": edges_created,
            "tokens": result["tokens"],
            "cost_usd": result["cost_usd"],
        }


async def search_memory_graph(user_id: str, query: str, top_k: int = 5) -> list[dict]:
    """Search the user's memory graph for nodes related to a query."""
    db = get_db()

    nodes = await db.memory_nodes.find(
        {"user_id": user_id},
        {"_id": 1, "label": 1, "description": 1, "embedding": 1, "task_ids": 1, "occurrence_count": 1}
    ).to_list(length=500)

    if not nodes:
        return []

    try:
        query_emb = await generate_embedding(query)
        query_vec = np.array(query_emb)
        scored = []
        for node in nodes:
            if node.get("embedding"):
                node_vec = np.array(node["embedding"])
                sim = float(np.dot(query_vec, node_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(node_vec) + 1e-10))
                scored.append((sim, node))
        scored.sort(reverse=True)
        return [{"label": n["label"], "description": n["description"], "task_ids": n["task_ids"], "score": round(s, 3)} for s, n in scored[:top_k]]
    except Exception as e:
        logger.warning("Memory search failed: %s", e)
        return []
