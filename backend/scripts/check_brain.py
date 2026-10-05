"""Quick check of ARC Brain data in MongoDB."""
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

async def main():
    from app.database import connect_db, get_db
    await connect_db()
    db = get_db()
    
    nodes = await db.memory_nodes.find({}).to_list(100)
    print(f"Total memory nodes: {len(nodes)}")
    for n in nodes:
        print(f"  - {n['label']} | type={n.get('node_type')} | tasks={n.get('task_ids',[])} | count={n.get('occurrence_count')}")
    
    edges = await db.memory_edges.find({}).to_list(100)
    print(f"\nTotal memory edges: {len(edges)}")
    
    # Check if nodes were created with empty data (failed LLM call)
    empty_nodes = [n for n in nodes if not n.get("embedding") or len(n.get("embedding",[])) == 0]
    print(f"\nNodes with missing embeddings: {len(empty_nodes)}")

if __name__ == "__main__":
    asyncio.run(main())
