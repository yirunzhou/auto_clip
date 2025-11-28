"""Helpers to merge raw caption segments into multi-sentence chunks."""

from __future__ import annotations
from typing import List, Tuple

SENTENCE_ENDINGS = {".", "?", "!", "…"}
TRAILING_CHARS = {'"', "'", "”", "’", ")"}


def chunk_segments(
    segments: List[dict],
    min_sentences: int = 2,
    max_sentences: int = 3,
) -> List[dict]:
    """Group raw caption segments into multi-sentence chunks.

    Chunks aim to cover 2-3 complete sentences so downstream LLM keyword
    extraction gets enough context to understand the story.
    """

    if not segments:
        return []

    sentences = _merge_segments_into_sentences(segments)
    if not sentences:
        return segments

    sentence_groups: List[List[dict]] = []
    current_group: List[dict] = []

    for sentence in sentences:
        current_group.append(sentence)
        if len(current_group) >= max_sentences:
            sentence_groups.append(current_group)
            current_group = []

    if current_group:
        if len(current_group) < min_sentences and sentence_groups:
            sentence_groups[-1].extend(current_group)
        else:
            sentence_groups.append(current_group)

    chunked = [_merge_sentence_group(group) for group in sentence_groups]
    return chunked


def _merge_sentence_group(group: List[dict]) -> dict:
    text = " ".join(sentence["text"] for sentence in group).strip()
    start = group[0]["start"]
    end = group[-1]["end"]
    segment_indices = []
    for sentence in group:
        segment_indices.extend(sentence["segment_indices"])
    return {
        "text": text,
        "start": start,
        "end": end,
        "segment_indices": segment_indices,
        "sentence_count": len(group),
    }


def _merge_segments_into_sentences(segments: List[dict]) -> List[dict]:
    full_text, spans = _build_full_text_with_spans(segments)
    if not full_text:
        return []

    sentences: List[dict] = []
    for start_char, end_char in _iterate_sentence_ranges(full_text):
        snippet = full_text[start_char:end_char].strip()
        if not snippet:
            continue
        segment_indices = _locate_segments(spans, start_char, end_char)
        if not segment_indices:
            continue
        start = segments[segment_indices[0]]["start"]
        end = segments[segment_indices[-1]]["end"]
        sentences.append(
            {
                "text": snippet,
                "start": start,
                "end": end,
                "segment_indices": segment_indices,
            }
        )

    return sentences


def _build_full_text_with_spans(segments: List[dict]) -> Tuple[str, List[Tuple[int, int, int]]]:
    parts: List[str] = []
    spans: List[Tuple[int, int, int]] = []
    cursor = 0
    for idx, seg in enumerate(segments):
        text = " ".join((seg.get("text") or "").split())
        if not text:
            continue
        if parts:
            parts.append(" ")
            cursor += 1
        start = cursor
        parts.append(text)
        cursor += len(text)
        spans.append((start, cursor, idx))
    return "".join(parts), spans


def _iterate_sentence_ranges(text: str) -> List[Tuple[int, int]]:
    ranges: List[Tuple[int, int]] = []
    start = 0
    i = 0
    length = len(text)
    while i < length:
        ch = text[i]
        if ch in SENTENCE_ENDINGS:
            end = i + 1
            while end < length and text[end] in TRAILING_CHARS:
                end += 1
            ranges.append((start, end))
            while end < length and text[end].isspace():
                end += 1
            start = end
            i = end
        else:
            i += 1
    if start < length:
        ranges.append((start, length))
    return ranges


def _locate_segments(
    spans: List[Tuple[int, int, int]], start_char: int, end_char: int
) -> List[int]:
    indices: List[int] = []
    for seg_start, seg_end, idx in spans:
        if seg_end <= start_char:
            continue
        if seg_start >= end_char:
            break
        indices.append(idx)
    return indices
