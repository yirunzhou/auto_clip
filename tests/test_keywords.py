from __future__ import annotations

import pytest

from auto_clip_lib import keywords as kw


def test_extract_keywords_raises_for_chinese_when_llm_missing(monkeypatch):
    segments = [{"text": "这是一段中文内容，需要 LLM 处理。"}]

    def fake_fetch(text):
        raise RuntimeError("LLM unavailable")

    monkeypatch.setattr(kw, "fetch_qwen_keywords", fake_fetch)

    with pytest.raises(RuntimeError):
        kw.extract_keywords(segments)
