"""Reusable helpers for running the metadata pipeline."""

from __future__ import annotations

from typing import Callable, Iterable

from .captions import parse_captions
from .chunking import chunk_segments
from .config import NO_SEARCH_RESULT, SEARCH_RESULTS
from .keywords import extract_keywords
from .queries import generate_queries
from .searchers import search_youtube


LogFn = Callable[[str], None]


def build_segments_metadata(
    srt_path: str,
    log_func: LogFn | None = print,
    search_providers: Iterable = None,
) -> list[dict]:
    """Run the caption → search pipeline and return enriched segments."""

    def _log(message: str) -> None:
        if log_func:
            log_func(message)

    segments = parse_captions(srt_path)
    _log(f"→ Parsed {len(segments)} base segments")

    segments = chunk_segments(segments)
    _log(f"→ Regrouped into {len(segments)} multi-sentence segments for search.")

    segments = extract_keywords(segments)
    _log("→ Extracted keywords for each segment.")

    providers = search_providers or ((search_youtube, "YouTube"),)
    for i, seg in enumerate(segments):
        query_candidates = generate_queries(seg)
        _log(f"[{i}] Searching: {query_candidates[0] if query_candidates else ''}")
        seg["queries_tried"] = query_candidates
        results = []

        for search_func, label in providers:
            source_hits = []
            last_query = query_candidates[0] if query_candidates else ""
            try:
                for attempt, query in enumerate(query_candidates):
                    last_query = query
                    source_hits = search_func(query, SEARCH_RESULTS)
                    if source_hits:
                        if attempt > 0:
                            _log(
                                f"  {label} retry #{attempt} succeeded with '{query}'"
                            )
                        break
                    if attempt < len(query_candidates) - 1:
                        _log(
                            NO_SEARCH_RESULT.format(
                                search_source=label, keywords=query
                            )
                        )
            except Exception as exc:  # pragma: no cover - network failures
                _log(f"  {label} search error: {exc}")
                source_hits = []
            if not source_hits:
                _log(
                    NO_SEARCH_RESULT.format(
                        search_source=label, keywords=last_query
                    )
                )
            results.extend(source_hits)

        seg["video_results"] = results

    return segments

