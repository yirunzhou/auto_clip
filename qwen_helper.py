import json
import os
import re
from typing import Any, List, Optional
from auto_clip_lib.utils import LLMQueryStatusError
import dashscope

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
DASHSCOPE_MODEL = os.getenv("DASHSCOPE_MODEL", "qwen-plus")
DASHSCOPE_ENDPOINT = os.getenv(
    "DASHSCOPE_ENDPOINT",
    'https://dashscope-intl.aliyuncs.com/api/v1'
)
dashscope.base_http_api_url = DASHSCOPE_ENDPOINT


def fetch_qwen_keywords(
    text: str,
    max_terms: int = 5,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
) -> List[str]:
    """Call DashScope Qwen to extract geopolitical keywords."""

    text = (text or "").strip()
    key = api_key or DASHSCOPE_API_KEY
    model = model_name or DASHSCOPE_MODEL
    prompt = (
        "You analyze news paragraphs to recommend b-roll searches. "
        "Return a JSON array (max 5 items) of short English keyword strings tuned for protests, press conferences, or military footage. "
        "Use these heuristics:\n"
        "- Activist or political groups → '<group name> protest' / 'rally' / 'march'.\n"
        "- Politicians or public figures → '<name> press conference', '<name> news conference', or '<name> briefing'.\n"
        "- Military branches or armed forces → '<unit> military drill', '<unit> war footage', '<unit> training'.\n"
        "- If none apply, still focus on combinations likely to yield news b-roll (crowds, briefings, demonstrations) rather than narrative sentences.\n"
        "Avoid dates and punctuation; just return the keyword phrases ready for YouTube search."
    )
    messages = [
        {'role': 'system', 'content': prompt},
        {'role': 'user', 'content': text}
    ]
    try:
        response = dashscope.Generation.call(
            api_key=key,
            model=model,
            messages=messages,
            result_format='text'
        )
        if response.status_code != 200:
            raise LLMQueryStatusError(f"Request failed: {response.status_code}, {response.message}")
    except Exception as exc:
        raise exc

    raw_text = _extract_raw_text(response)
    keywords = parse_keyword_list(raw_text)
    return keywords[:max_terms]


def parse_keyword_list(value: Optional[str]) -> List[str]:
    if not value:
        return []
    value = value.strip()
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    except json.JSONDecodeError:
        pass
    parts = re.split(r"[,;\n]+", value)
    keywords = []
    for part in parts:
        cleaned = part.strip(" -\t\"'")
        if cleaned:
            keywords.append(cleaned)
    return keywords


def _extract_raw_text(payload: Any) -> str:
    """Handle DashScope responses regardless of schema (text, dict, or objects)."""
    if payload is None:
        return ""
    if isinstance(payload, str):
        return payload
    if isinstance(payload, list):
        parts = []
        for item in payload:
            text_value = _extract_raw_text(item)
            if text_value:
                parts.append(text_value)
        return "".join(parts).strip()

    # Objects returned by dashscope (e.g., GenerationResponse/GenerationOutput)
    text_value = _safe_getattr(payload, "text")
    if isinstance(text_value, str):
        return text_value

    for attr in ("output", "message", "content"):
        nested = _safe_getattr(payload, attr)
        text_value = _extract_raw_text(nested)
        if text_value:
            return text_value

    choices = _safe_getattr(payload, "choices")
    if isinstance(choices, list):
        for choice in choices:
            text_value = _extract_raw_text(choice)
            if text_value:
                return text_value

    if isinstance(payload, dict):
        if isinstance(payload.get("text"), str):
            return payload["text"]
        for key in ("output", "message", "content"):
            text_value = _extract_raw_text(payload.get(key))
            if text_value:
                return text_value
        choices = payload.get("choices")
        if isinstance(choices, list):
            for choice in choices:
                text_value = _extract_raw_text(choice)
                if text_value:
                    return text_value
    return ""


def _safe_getattr(obj: Any, attr: str) -> Any:
    try:
        return getattr(obj, attr)
    except (AttributeError, KeyError):
        return None


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Test Qwen geopolitical keyword extraction."
    )
    parser.add_argument(
        "text", type=str, nargs="?", help="Sentence to analyze (positional)."
    )
    parser.add_argument(
        "--text",
        dest="text_option",
        type=str,
        help="Sentence to analyze (optional flag alternative).",
    )
    parser.add_argument(
        "--max-terms", type=int, default=5, help="Maximum keywords to return."
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Override DashScope model name (defaults to env).",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="Override DashScope API key (defaults to env).",
    )
    args = parser.parse_args()
    text_value = args.text_option or args.text
    if not text_value:
        parser.error("Provide the sentence via positional TEXT or --text option.")

    keywords = fetch_qwen_keywords(
        text_value,
        max_terms=args.max_terms,
        api_key=args.api_key,
        model_name=args.model,
    )
    print(json.dumps(keywords, ensure_ascii=False, indent=2))
