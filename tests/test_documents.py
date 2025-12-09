from __future__ import annotations

from auto_clip_lib.documents import parse_document, _is_chinese_dominant, _normalize_text


def test_parse_document_filters_chinese_paragraphs(fixtures_dir):
    doc_path = fixtures_dir / "sample.docx"
    segments = parse_document(doc_path)

    assert len(segments) == 6
    english = [seg for seg in segments if not seg["has_chinese"]]
    chinese = [seg for seg in segments if seg["has_chinese"]]
    assert english[0]["text"].startswith("First English")
    assert english[-1]["text"].startswith("Fifth English")
    assert english[0]["start"] == 0.0
    assert english[-1]["start"] == 5.0
    assert len(chinese) == 1
    assert "中文" in chinese[0]["text"]


def test_is_chinese_dominant_thresholds():
    assert _is_chinese_dominant("完全中文内容")
    assert not _is_chinese_dominant("All English words only")
    assert _is_chinese_dominant("中文中文中文中文 mixed english", threshold=0.3)


def test_normalize_text_collapses_whitespace():
    text = " Title  \n\n goes\t here "
    assert _normalize_text(text) == "Title goes here"
