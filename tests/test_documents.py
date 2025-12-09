from __future__ import annotations

import zipfile
from pathlib import Path

from auto_clip_lib.documents import (
    parse_document,
    _is_chinese_dominant,
    _normalize_text,
)


def _write_docx(path: Path, paragraphs: list[str]) -> None:
    body = "".join(
        f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>" for text in paragraphs
    )
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}</w:body></w:document>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">"
        "<Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>"
        "<Default Extension=\"xml\" ContentType=\"application/xml\"/>"
        "<Override PartName=\"/word/document.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml\"/>"
        "</Types>"
    )
    rels_root = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
        "<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"word/document.xml\"/>"
        "</Relationships>"
    )

    with zipfile.ZipFile(path, "w") as doc:
        doc.writestr("[Content_Types].xml", content_types)
        doc.writestr("_rels/.rels", rels_root)
        doc.writestr("word/document.xml", document_xml)


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


def test_parse_document_retains_chinese_segments(tmp_path):
    doc_path = tmp_path / "mixed.docx"
    _write_docx(
        doc_path,
        [
            "完全中文段落包含大量汉字和描述。",
            "English paragraph follows the Chinese lead-in.",
        ],
    )
    segments = parse_document(doc_path)
    assert any(seg["has_chinese"] for seg in segments)
    assert any(not seg["has_chinese"] for seg in segments)


def test_is_chinese_dominant_thresholds():
    assert _is_chinese_dominant("完全中文内容")
    assert not _is_chinese_dominant("All English words only")
    assert _is_chinese_dominant("中文中文中文中文 mixed english", threshold=0.3)


def test_normalize_text_collapses_whitespace():
    text = " Title  \n\n goes\t here "
    assert _normalize_text(text) == "Title goes here"
