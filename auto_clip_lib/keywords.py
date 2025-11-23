"""Keyword extraction helpers."""

from keybert import KeyBERT

from qwen_helper import fetch_qwen_keywords


_kw_model: KeyBERT | None = None


def _get_model() -> KeyBERT:
    global _kw_model
    if _kw_model is None:
        _kw_model = KeyBERT()
    return _kw_model


def extract_keywords(segments: list[dict]) -> list[dict]:
    kw_model = _get_model()
    for seg in segments:
        text = seg["text"]
        keywords = fetch_qwen_keywords(text)
        if not keywords:
            keywords = kw_model.extract_keywords(
                text, keyphrase_ngram_range=(1, 2), stop_words="english"
            )
        seg["keywords"] = keywords[:5]
    return segments
