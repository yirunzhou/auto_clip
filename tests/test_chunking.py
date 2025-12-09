from __future__ import annotations

from auto_clip_lib.chunking import chunk_segments


def _make_segment(text: str, start: float, end: float) -> dict:
    return {"text": text, "start": start, "end": end}


def test_chunk_segments_groups_sentences():
    segments = [
        _make_segment(
            "Sentence one ends here. Sentence two carries on.",
            0,
            2,
        ),
        _make_segment(
            "Sentence three keeps going. Sentence four wraps things up.",
            2,
            4,
        ),
        _make_segment("Sentence five stands alone.", 4, 5),
    ]

    chunked = chunk_segments(segments, min_sentences=1, max_sentences=2)

    assert len(chunked) == 3
    assert chunked[0]["sentence_count"] == 2
    assert chunked[0]["text"].startswith("Sentence one ends")
    assert chunked[1]["sentence_count"] == 2
    assert "Sentence three" in chunked[1]["text"]
    assert chunked[2]["sentence_count"] == 1
    assert chunked[2]["text"] == "Sentence five stands alone."


def test_chunk_segments_returns_original_when_no_sentences():
    segments = [
        _make_segment("", 0, 1),
        _make_segment("   ", 1, 2),
    ]
    result = chunk_segments(segments)
    assert result == segments
