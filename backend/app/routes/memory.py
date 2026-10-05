"""
ARC Platform — Memory Graph Routes
GET /memory/graph  — returns nodes + edges for visualization
GET /memory/search — search nodes by query
DELETE /memory/{node_id} — delete a node
"""
from fastapi import APIRouter, Depends, HTTPException
from app.database import get_db
from app.deps import get_current_user

router = APIRouter()


@router.get("/graph")
async def get_memory_graph(current_user: dict = Depends(get_current_user)):
    """Returns the user's full memory graph for visualization."""
    db = get_db()
    user_id = current_user["_id"]

    nodes = await db.memory_nodes.find(
        {"user_id": user_id},
        {"embedding": 0}  # exclude embeddings from response (too large)
    ).sort("occurrence_count", -1).to_list(length=200)

    edges = await db.memory_edges.find(
        {"user_id": user_id}
    ).sort("weight", -1).to_list(length=1000)

    return {
        "nodes": [
            {
                "id": n["_id"],
                "label": n["label"],
                "type": n.get("node_type", "topic"),
                "description": n.get("description", ""),
                "task_count": len(n.get("task_ids", [])),
                "occurrence_count": n.get("occurrence_count", 1),
            }
            for n in nodes
        ],
        "edges": [
            {
                "id": e["_id"],
                "from": e["from_node_id"],
                "to": e["to_node_id"],
                "weight": round(e.get("weight", 1.0), 2),
            }
            for e in edges
        ],
        "total_nodes": len(nodes),
        "total_edges": len(edges),
    }


@router.get("/search")
async def search_memory(query: str, current_user: dict = Depends(get_current_user)):
    """Search memory graph by semantic similarity."""
    from app.agents.memory import search_memory_graph
    results = await search_memory_graph(current_user["_id"], query, top_k=8)
    return {"results": results, "query": query}


@router.delete("/{node_id}")
async def delete_memory_node(node_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a memory node and its edges."""
    db = get_db()
    user_id = current_user["_id"]
    result = await db.memory_nodes.delete_one({"_id": node_id, "user_id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Node not found")
    await db.memory_edges.delete_many({
        "user_id": user_id,
        "$or": [{"from_node_id": node_id}, {"to_node_id": node_id}]
    })
    return {"success": True}
