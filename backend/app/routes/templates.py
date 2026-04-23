from typing import Any
from fastapi import APIRouter
from app.database import get_db

router = APIRouter()

SEED_TEMPLATES = [
    {
        "title": "Literature Review",
        "description": "Comprehensive academic literature review summarizing the state of the art, methodologies, and gaps in current research.",
        "suggested_budget": 3.00,
        "suggested_tags": ["academic", "research", "review"],
        "example_prompts": [
            "Conduct a literature review on recent advances in quantum error correction.",
            "Summarize the efficacy of CRISPR-Cas9 therapies over the last 5 years."
        ]
    },
    {
        "title": "Market Analysis",
        "description": "Deep dive into industry trends, competitor positioning, market size, and future growth projections.",
        "suggested_budget": 4.50,
        "suggested_tags": ["business", "market", "strategy"],
        "example_prompts": [
            "Analyze the electric vehicle market in Southeast Asia.",
            "Identify key competitors and market share in the AI SaaS space."
        ]
    },
    {
        "title": "Data Exploration",
        "description": "Statistically analyze open datasets, extract correlations, and write Python code to visualize patterns.",
        "suggested_budget": 2.50,
        "suggested_tags": ["data", "coding", "analysis"],
        "example_prompts": [
            "Fetch stock market data for Apple and Microsoft and trend their volatility.",
            "Analyze global temperature anomalies dataset and visualize the trajectory."
        ]
    },
    {
        "title": "Code Review",
        "description": "Examine GitHub repositories or provided codebases for security vulnerabilities, optimizations, and technical debt.",
        "suggested_budget": 3.50,
        "suggested_tags": ["programming", "security", "audit"],
        "example_prompts": [
            "Review best practices and security flaws in typical Next.js authentication flows.",
            "Analyze the Linux kernel's recent networking patch for potential bottlenecks."
        ]
    },
    {
        "title": "Competitive Analysis",
        "description": "Head-to-head comparison of products or companies detailing pricing, feature sets, and user sentiment.",
        "suggested_budget": 2.00,
        "suggested_tags": ["marketing", "product", "comparison"],
        "example_prompts": [
            "Compare the pricing and features of Stripe vs Paddle vs LemonSqueezy.",
            "Evaluate user sentiment and feature gaps between Figma and Sketch."
        ]
    }
]

async def seed_templates():
    """Seeds the templates collection if it is empty."""
    db = get_db()
    count = await db.templates.count_documents({})
    if count == 0:
        await db.templates.insert_many(SEED_TEMPLATES)

@router.get("")
async def list_templates() -> dict[str, Any]:
    """List all available task templates."""
    db = get_db()
    cursor = db.templates.find({})
    templates = await cursor.to_list(None)
    
    formatted_templates = []
    for t in templates:
        t["id"] = str(t.pop("_id"))
        formatted_templates.append(t)
        
    return {
        "success": True,
        "data": formatted_templates,
        "message": "Templates fetched successfully"
    }
