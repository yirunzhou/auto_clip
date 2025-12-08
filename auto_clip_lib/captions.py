"""Caption parsing and alignment helpers."""

from __future__ import annotations

import pysrt
import torch
from sentence_transformers import SentenceTransformer, util

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def parse_captions(srt_path: str) -> list[dict]:
    try:
        subs = pysrt.open(srt_path)
    except Exception:
        return []
    segments = []
    for s in subs:
        start = s.start.ordinal / 1000
        end = s.end.ordinal / 1000
        text = s.text.replace("\n", " ").strip()
        if text:
            segments.append({"start": start, "end": end, "text": text})
    return segments


def find_best_segment(original_text: str, transcript_segments: list[dict]) -> dict | None:
    if not transcript_segments:
        return None

    model = _get_model()
    original_embedding = model.encode(original_text, convert_to_tensor=True)
    transcript_texts = [seg["text"] for seg in transcript_segments]
    transcript_embeddings = model.encode(transcript_texts, convert_to_tensor=True)

    cos_scores = util.cos_sim(original_embedding, transcript_embeddings)[0]
    best_match_idx = torch.argmax(cos_scores).item()

    return transcript_segments[best_match_idx]
