import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add backend dir to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.research import ResearchAgent
from app.agents.data import DataAgent
from app.agents.code import CodeAgent
from app.agents.base import BaseAgent
from app.models.agent import AgentType
from app.database import connect_db, connect_redis

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("eval")

EVALS_DIR = Path(__file__).parent
GOLDEN_TASKS_PATH = EVALS_DIR / "golden_tasks.json"
RESULTS_DIR = EVALS_DIR / "results"

class JudgeAgent(BaseAgent):
    """Standalone agent to score eval outputs."""
    agent_type = AgentType.CRITIC
    system_prompt = """You are an expert evaluator grading the output of AI agents against a specific rubric.
Given the original task, the rubric, and the agent's output, score the output from 1 to 5 based on how well it satisfies the rubric.

Score criteria:
1: Fails to meet any rubric criteria or produced an error.
2: Meets only 1 rubric criterion or has major flaws.
3: Meets most rubric criteria but has significant omissions.
4: Meets all rubric criteria but lacks polish or has minor issues.
5: Meets all rubric criteria perfectly.

Output a JSON object:
{
  "score": <int 1-5>,
  "justification": "<one sentence explaining the score>"
}"""

    async def run(self, input_data: dict) -> dict:
        messages = [{
            "role": "user",
            "content": f"""Task: {input_data['task']['title']}
Description: {input_data['task']['description']}

Rubric:
{json.dumps(input_data['task']['rubric'], indent=2)}

Agent Output:
{json.dumps(input_data['agent_output'], indent=2)}"""
        }]

        result = await self.call_llm(
            messages,
            response_format={"type": "json_object"}
        )
        return await self.parse_json_response(result["content"])

async def run_evals():
    await connect_db()
    await connect_redis()
    from app.tools.registry import register_all_tools, tool_registry
    if not tool_registry._tools:
        register_all_tools()
    
    with open(GOLDEN_TASKS_PATH) as f:
        tasks = json.load(f)

    judge = JudgeAgent(task_id="eval_run", step_id="eval_step", user_id="eval_user")
    
    results = []
    print("\n" + "="*80)
    print(f"{'Task Title':<45} | {'Score':<5} | {'Justification'}")
    print("="*80)

    total_score = 0
    
    for task in tasks:
        agent_cls = {
            "research": ResearchAgent,
            "data": DataAgent,
            "code": CodeAgent
        }.get(task["task_type"])

        if not agent_cls:
            logger.error(f"Unknown task type: {task['task_type']}")
            continue

        agent = agent_cls(task_id="eval_run", step_id="eval_step", user_id="eval_user")
        
        # Mock input
        input_data = {
            "title": task["title"],
            "description": task["description"],
            "step_description": task["description"],
            "task_description": task["description"],
            "query": task["description"],
            "dependency_outputs": {}
        }
        
        try:
            agent_output = await agent.run(input_data)
        except Exception as e:
            agent_output = {"error": str(e)}

        # Score it
        try:
            judge_res = await judge.run({"task": task, "agent_output": agent_output})
            score = judge_res.get("score", 1)
            justification = judge_res.get("justification", "Failed to parse judge output.")
        except Exception as e:
            score = 1
            justification = f"Judge error: {e}"

        total_score += score
        
        results.append({
            "task_title": task["title"],
            "agent_output": agent_output,
            "score": score,
            "justification": justification
        })

        # Print row
        print(f"{task['title'][:43]:<45} | {score:<5} | {justification[:60]}")

    print("="*80)
    
    avg_score = total_score / len(tasks) if tasks else 0
    print(f"\nAverage Score: {avg_score:.2f} / 5.0")

    # Compare baseline
    baseline_path = RESULTS_DIR / "baseline.json"
    if baseline_path.exists():
        try:
            with open(baseline_path) as f:
                baseline_data = json.load(f)
                if "average_score" in baseline_data:
                    diff = avg_score - baseline_data["average_score"]
                    print(f"Versus Baseline: {diff:+.2f} (Baseline: {baseline_data['average_score']:.2f})")
        except json.JSONDecodeError:
            pass # Empty or invalid placeholder
    else:
        print("No valid baseline exists yet.")

    # Save results
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = RESULTS_DIR / f"{timestamp}.json"
    
    run_data = {
        "timestamp": timestamp,
        "average_score": avg_score,
        "results": results
    }
    
    with open(out_path, "w") as f:
        json.dump(run_data, f, indent=2)
        
    print(f"Results saved to {out_path}\n")

if __name__ == "__main__":
    asyncio.run(run_evals())
