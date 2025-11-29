"""Keyword extraction helpers."""

from typing import Iterable, List

from keybert import KeyBERT

from qwen_helper import fetch_qwen_keywords

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
        except Exception as exce:
            raise exce
        seg["keywords"] = _normalize_keywords(keywords)[:5]
    return segments


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
