import asyncio
import json
import logging
import re
from typing import Any, AsyncGenerator

from litellm import acompletion
from litellm.exceptions import RateLimitError
from app.config import get_settings

logger = logging.getLogger("arc.agents.llm_client")

class MockChoice:
    def __init__(self, content: str):
        self.message = type("Message", (), {"content": content, "tool_calls": []})()

class MockUsage:
    def __init__(self):
        self.prompt_tokens = 200
        self.completion_tokens = 200
        self.total_tokens = 400

class MockResponse:
    def __init__(self, content: str, model: str):
        self.choices = [MockChoice(content)]
        self.model = model
        self.usage = MockUsage()

def normalize_model(m: str) -> str:
    if not m.startswith("groq/"):
        return f"groq/{m}"
    return m

def extract_failed_generation(e: Exception) -> str | None:
    """Extract valid output/arguments from failed tool call generations in Groq/LiteLLM exceptions."""
    body = getattr(e, "body", None)
    failed_gen = None
    if isinstance(body, dict):
        failed_gen = body.get("error", {}).get("failed_generation")

    if not failed_gen:
        err_str = str(e)
        if "failed_generation" in err_str:
            import re
            m = re.search(r'"failed_generation"\s*:\s*("(?:\\.|[^"\\])*")', err_str)
            if m:
                try:
                    failed_gen = json.loads(m.group(1))
                except Exception:
                    failed_gen = m.group(1)

    if failed_gen and isinstance(failed_gen, str):
        # Try JSON parse
        try:
            parsed = json.loads(failed_gen)
            if isinstance(parsed, dict) and "arguments" in parsed:
                args = parsed["arguments"]
                return json.dumps(args) if isinstance(args, (dict, list)) else str(args)
            return failed_gen
        except Exception:
            # If arguments is raw unquoted code or text
            if '"arguments":' in failed_gen:
                start = failed_gen.find('"arguments":') + len('"arguments":')
                raw_args = failed_gen[start:].strip()
                if raw_args.endswith("}"):
                    raw_args = raw_args[:-1].strip()
                return raw_args
            return failed_gen

    return None

async def chat_completion(
    messages: list[dict[str, Any]],
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 2048,
    response_format: dict[str, Any] | None = None,
    tools: list[dict[str, Any]] | None = None,
    stream: bool = False,
) -> Any:
    """
    Call LLM with automatic rate-limit backoff, tool-call recovery, and fallback support using litellm.
    """
    settings = get_settings()
    
    raw_fallbacks = settings.LLM_FALLBACK_ROUTING.copy()
    formatted_fallbacks = [normalize_model(f) for f in raw_fallbacks]
    
    primary = model or settings.GROQ_MODEL
    primary_model = normalize_model(primary)
    
    # Models to attempt in order
    model_chain = [primary_model] + [fb for fb in formatted_fallbacks if fb != primary_model]
    
    kwargs = {
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": stream,
        "api_key": settings.GROQ_API_KEY,
    }
    if response_format:
        kwargs["response_format"] = response_format
    if tools:
        kwargs["tools"] = tools

    last_exception = None

    for candidate_model in model_chain:
        # Retry with exponential backoff on 429 / RateLimitError
        max_rate_limit_retries = 3
        for attempt in range(max_rate_limit_retries):
            try:
                response = await acompletion(
                    model=candidate_model,
                    **kwargs
                )
                return response
            except RateLimitError as rle:
                last_exception = rle
                err_str = str(rle)
                if "tokens per day" in err_str or "TPD" in err_str:
                    logger.warning(f"Daily token limit reached for {candidate_model}. Immediately trying next fallback model...")
                    break

                wait_seconds = 2.0 * (attempt + 1)
                match = re.search(r"try again in ([\d\.]+)s", err_str, re.IGNORECASE)
                if match:
                    try:
                        parsed_wait = float(match.group(1))
                        if parsed_wait > 30.0:
                            logger.warning(f"Rate limit wait time {parsed_wait}s too long for {candidate_model}. Immediately trying next fallback model...")
                            break
                        wait_seconds = min(parsed_wait + 0.5, 10.0)
                    except ValueError:
                        pass
                logger.warning(
                    f"Rate limit hit for {candidate_model} (attempt {attempt + 1}/{max_rate_limit_retries}). "
                    f"Waiting {wait_seconds:.2f}s before retrying..."
                )
                if attempt < max_rate_limit_retries - 1:
                    await asyncio.sleep(wait_seconds)
                else:
                    logger.warning(f"Exceeded retries on {candidate_model}, attempting next fallback model...")
            except Exception as e:
                # Check if this error contains a valid failed_generation (e.g. LLM called nonexistent tool 'json')
                recovered_content = extract_failed_generation(e)
                if recovered_content:
                    logger.info(f"Recovered valid output from tool call error on {candidate_model}")
                    return MockResponse(recovered_content, candidate_model)

                last_exception = e
                logger.warning(f"LLM call to {candidate_model} failed: {e}. Trying next model...")
                break  # Don't retry non-rate-limit errors on the same model, switch to next model

    logger.error(f"All models in chain failed: {last_exception}")
    raise last_exception


async def stream_chat_completion(
    messages: list[dict[str, Any]],
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 2048,
) -> AsyncGenerator[str, None]:
    """
    Stream chunks from LLM.
    """
    response = await chat_completion(
        messages=messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True
    )
    
    async for chunk in response:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
