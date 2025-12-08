"""Document parsing helpers for .docx inputs."""

from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import List
from xml.etree import ElementTree as ET

DOCX_MAIN = "word/document.xml"
WORD_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
TEXT_TAG = f"{WORD_NS}t"
TAB_TAG = f"{WORD_NS}tab"
BREAK_TAG = f"{WORD_NS}br"

HAN_REGEX = re.compile(r"[\u4E00-\u9FFF]")
ASCII_REGEX = re.compile(r"[A-Za-z]")
WHITESPACE_REGEX = re.compile(r"\s+")


def parse_document(doc_path: str | Path) -> list[dict]:
    """Return caption-like segments from a DOCX file, skipping Chinese paragraphs."""

    path = Path(doc_path)
    if not path.exists():
        return []

    suffix = path.suffix.lower()
    if suffix == ".doc":
        raise ValueError("Legacy .doc files are not supported; convert to .docx first.")
    if suffix != ".docx":
        raise ValueError(f"Unsupported document type: {suffix or 'unknown'}")

    paragraphs = _load_docx_paragraphs(path)

    english_only = []
    for paragraph in paragraphs:
        text = _normalize_text(paragraph)
        if not text or _is_chinese_dominant(text):
            continue
        english_only.append(text)

    segments: list[dict] = []
    for idx, text in enumerate(english_only):
        segments.append(
            {
                "start": float(idx),
                "end": float(idx + 1),
                "text": text,
                "paragraph_index": idx,
            }
        )
    return segments


def _load_docx_paragraphs(path: Path) -> List[str]:
    try:
        with zipfile.ZipFile(path) as doc:
            xml_bytes = doc.read(DOCX_MAIN)
    except (FileNotFoundError, zipfile.BadZipFile, KeyError):
        return []

    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return []

    paragraphs: List[str] = []
    for paragraph in root.iter(f"{WORD_NS}p"):
        text = _extract_paragraph_text(paragraph)
        if text:
            paragraphs.append(text)
    return paragraphs


def _extract_paragraph_text(paragraph: ET.Element) -> str:
    pieces: List[str] = []
    for node in paragraph.iter():
        if node.tag == TEXT_TAG and node.text:
            pieces.append(node.text)
        elif node.tag in (TAB_TAG, BREAK_TAG):
            pieces.append(" ")
    return "".join(pieces)


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    cleaned = text.replace("\u00A0", " ").strip()
    return WHITESPACE_REGEX.sub(" ", cleaned)


def _is_chinese_dominant(text: str, threshold: float = 0.5) -> bool:
    han_count = len(HAN_REGEX.findall(text))
    ascii_count = len(ASCII_REGEX.findall(text))
    if not ascii_count and not han_count:
        return True
    if han_count == 0:
        return False
    if ascii_count == 0:
        return True
    total = han_count + ascii_count
    return (han_count / total) >= threshold
