from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

import pytest


@pytest.fixture()
def fixtures_dir() -> Path:
    return Path(__file__).parent / "data"


def _fake_search_factory(results: list[dict]) -> Callable[[str, int], list[dict]]:
    def _fake(query: str, limit: int) -> list[dict]:
        return results

    return _fake


def _fake_llm(text: str, max_terms: int = 5, api_key=None, model_name=None) -> list[str]:
    base = text.split()[0] if text else "clip"
    return [f"{base} protest"]


@pytest.fixture()
def stub_llm(monkeypatch):
    monkeypatch.setattr(
        "auto_clip_lib.keywords.fetch_qwen_keywords", _fake_llm
    )


@pytest.fixture()
def fake_search(monkeypatch):
    hits = [
        {
            "id": "abc123",
            "title": "Stub hit",
            "url": "https://example.com",
            "source": "YouTube",
            "channel": "News",
        }
    ]
    return _fake_search_factory(hits)
