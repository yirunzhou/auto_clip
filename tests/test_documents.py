from __future__ import annotations

from auto_clip_lib.documents import parse_document


def test_parse_document_filters_chinese_paragraphs(fixtures_dir):
    doc_path = fixtures_dir / "sample.docx"
    segments = parse_document(doc_path)

    assert len(segments) == 5
    assert segments[0]["text"].startswith("First English")
    assert segments[-1]["text"].startswith("Fifth English")
    assert segments[0]["start"] == 0.0
    assert segments[-1]["start"] == 4.0
