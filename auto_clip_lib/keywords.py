"""Keyword extraction helpers."""

import logging
import re
from typing import Iterable, List, Tuple

import jieba
import torch
from keybert import KeyBERT
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import CountVectorizer

from qwen_helper import fetch_qwen_keywords

LOGGER = logging.getLogger(__name__)

HAN_REGEX = re.compile(r"[\u4E00-\u9FFF]")

_kw_model: KeyBERT | None = None
_translator_bundle: Tuple | None = None
_jieba_vectorizer: CountVectorizer | None = None


def _get_model() -> KeyBERT:
    global _kw_model
    if _kw_model is None:
        transformer = SentenceTransformer(
            "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
        )
        _kw_model = KeyBERT(model=transformer)
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
                text,
                vectorizer=_get_vectorizer(text),
                keyphrase_ngram_range=(1, 2),
                stop_words=None,
            )
        normalized = _normalize_keywords(keywords)[:5]
        seg["keywords"] = [_maybe_translate_keyword(keyword) for keyword in normalized]
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


def _maybe_translate_keyword(keyword: str) -> str:
    if not keyword or not HAN_REGEX.search(keyword):
        return keyword
    try:
        model, tokenizer, device = _get_translator()
        tokenizer.tgt_lang = "en"
        prefixed = f"en: {keyword}"
        inputs = tokenizer(prefixed, return_tensors="pt").to(device)
        with torch.no_grad():
            generated = model.generate(**inputs, max_length=96)
        translation = tokenizer.decode(
            generated[0], skip_special_tokens=True
        ).strip()
        translation = re.sub(r"^(en|En)\s*:\s*", "", translation).strip()
        return translation or keyword
    except Exception:  # pragma: no cover - translation failures
        LOGGER.warning(
            "Keyword translation failed; keeping original. keyword=%r",
            keyword,
            exc_info=True,
        )
    return keyword


def _get_translator():
    global _translator_bundle
    if _translator_bundle is None:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        model_id = "alirezamsh/small100"
        tokenizer = AutoTokenizer.from_pretrained(
            model_id, trust_remote_code=True
        )
        model = AutoModelForSeq2SeqLM.from_pretrained(
            model_id, trust_remote_code=True
        )
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model.to(device)
        _translator_bundle = (model, tokenizer, device)
    return _translator_bundle


def _get_vectorizer(text: str) -> CountVectorizer | None:
    if HAN_REGEX.search(text):
        global _jieba_vectorizer
        if _jieba_vectorizer is None:
            def _jieba_tokenizer(value: str) -> list[str]:
                return list(jieba.cut(value))

            _jieba_vectorizer = CountVectorizer(
                tokenizer=_jieba_tokenizer,
                token_pattern=None,
                ngram_range=(1, 2),
            )
        return _jieba_vectorizer
    return None
