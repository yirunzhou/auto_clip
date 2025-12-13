from __future__ import annotations

from auto_clip_lib import keywords as kw


class DummyModel:
    def extract_keywords(self, text, **_kwargs):
        return [("示例关键词", 0.9)]


def test_extract_keywords_fallback_handles_chinese(monkeypatch):
    segments = [{"text": "这是一段中文内容，需要本地模型处理。"}]

    def fake_fetch(text):
        raise RuntimeError("LLM unavailable")

    def fake_translator():
        import torch

        class FakeInputs(dict):
            def to(self, device):
                return self

        class FakeTokenizer:
            tgt_lang = None

            def __call__(self, text, return_tensors="pt"):
                self.last_input = text
                return FakeInputs({"input_ids": torch.ones((1, 3), dtype=torch.long)})

            def decode(self, ids, skip_special_tokens=True):
                return "en: translated keyword"

        class FakeModel:
            def to(self, device):
                return self

            def generate(self, **kwargs):
                return torch.ones((1, 5), dtype=torch.long)

        return FakeModel(), FakeTokenizer(), torch.device("cpu")

    monkeypatch.setattr(kw, "fetch_qwen_keywords", fake_fetch)
    monkeypatch.setattr(kw, "_get_model", lambda: DummyModel())
    monkeypatch.setattr(kw, "_get_translator", fake_translator)

    result = kw.extract_keywords(segments)
    assert result[0]["keywords"][0] == "translated keyword"
