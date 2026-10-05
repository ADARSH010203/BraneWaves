import json
import logging
from typing import Any

import tiktoken

logger = logging.getLogger("arc.agents.context_utils")

def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    """Return the number of tokens in a text using tiktoken."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))

def truncate_to_tokens(text: str, max_tokens: int, model: str = "gpt-3.5-turbo") -> str:
    """Truncate a string to a maximum number of tokens."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    
    tokens = encoding.encode(text)
    if len(tokens) <= max_tokens:
        return text
    
    return encoding.decode(tokens[:max_tokens]) + "..."

async def compress_dependency_output(output: dict[str, Any], max_tokens: int = 300, llm_call_fn=None) -> str:
    """
    Compress dependency output to fit within max_tokens.
    Extracts relevant fields (summary, key_findings, analysis) and skips raw tool results.
    """
    # Quick serialization to check if it's already under limits
    raw_str = json.dumps(output)
    if count_tokens(raw_str) <= max_tokens:
        return raw_str

    # Extract relevant fields
    compressed = {}
    for key in ["summary", "key_findings", "analysis", "statistics", "code", "explanation"]:
        if key in output:
            compressed[key] = output[key]

    compressed_str = json.dumps(compressed)
    if count_tokens(compressed_str) <= max_tokens:
        return compressed_str

    # Still too large, do aggressive truncation on strings
    final_output = {}
    budget_per_key = max_tokens // len(compressed) if compressed else max_tokens
    
    for k, v in compressed.items():
        if isinstance(v, str):
            # rough estimate: 4 chars per token
            char_limit = budget_per_key * 4
            final_output[k] = v[:char_limit] + "..."
        elif isinstance(v, list):
            # take first few items
            final_output[k] = v[:3]
        else:
            final_output[k] = v

    return json.dumps(final_output)
