from __future__ import annotations

from auto_clip_lib.documents import (
    parse_document,
    _is_chinese_dominant,
    _normalize_text,
)


def test_parse_document_filters_chinese_paragraphs(fixtures_dir):
    doc_path = fixtures_dir / "sample.docx"
    segments = parse_document(doc_path)

    assert len(segments) == 5
    assert segments[0]["text"].startswith("First English")
    assert segments[-1]["text"].startswith("Fifth English")
    assert segments[0]["start"] == 0.0
    assert segments[-1]["start"] == 4.0


def test_is_chinese_dominant_thresholds():
    assert _is_chinese_dominant("完全中文内容")
    assert not _is_chinese_dominant("All English words only")
    assert _is_chinese_dominant("中文中文中文中文 mixed english", threshold=0.3)


def test_normalize_text_collapses_whitespace():
    text = " Title  \n\n goes\t here "
    assert _normalize_text(text) == "Title goes here"
