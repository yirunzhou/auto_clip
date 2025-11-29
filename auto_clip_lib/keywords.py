"""Keyword extraction helpers."""

import logging
from typing import Iterable, List

from keybert import KeyBERT

from qwen_helper import fetch_qwen_keywords

LOGGER = logging.getLogger(__name__)

_kw_model: KeyBERT | None = None


def _get_model() -> KeyBERT:
    global _kw_model
    if _kw_model is None:
        _kw_model = KeyBERT()
    return _kw_model


def extract_keywords(segments: list[dict]) -> list[dict]:
    """Attach keyword lists to each multi-sentence segment."""

    if not segments:
        return []

    kw_model = _get_model()
    for seg in segments:
        text = seg["text"]
        try:
            keywords = fetch_qwen_keywords(text)
            seg["_keyword_source"] = "llm"
        except Exception:  # pragma: no cover - service/network failures
            snippet = _build_snippet(text)
            LOGGER.warning(
                "LLM keyword extraction unavailable; falling back to local KeyBERT. "
                "snippet=%r",
                snippet or "<empty>",
                exc_info=True,
            )
            seg["_keyword_source"] = "keybert"
            keywords = kw_model.extract_keywords(
                text, keyphrase_ngram_range=(1, 2), stop_words="english"
            )
        seg["keywords"] = _normalize_keywords(keywords)[:5]
    return segments


def _build_snippet(text: str, limit: int = 120) -> str:
    snippet = (text or "").strip().replace("\n", " ")
    if len(snippet) > limit:
        return snippet[:limit] + "..."
    return snippet


def _normalize_keywords(candidates: Iterable) -> List[str]:
    normalized: List[str] = []
    for candidate in candidates:
        if isinstance(candidate, (list, tuple)):
            if not candidate:
                continue
            value = candidate[0]
        else:
            value = candidate
        text = str(value).strip()
        if text:
            normalized.append(text)
    return normalized
