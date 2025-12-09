from __future__ import annotations

from auto_clip_lib.pipeline import build_segments_metadata


def test_pipeline_with_srt(fixtures_dir, fake_search, stub_llm):
    srt_path = fixtures_dir / "sample.srt"

    segments = build_segments_metadata(
        str(srt_path),
        log_func=None,
        search_providers=((fake_search, "StubTube"),),
    )

    assert segments
    for seg in segments:
        assert seg["keywords"]
        assert seg["video_results"]
        assert seg["queries_tried"]


def test_pipeline_with_docx(fixtures_dir, fake_search, stub_llm):
    docx_path = fixtures_dir / "sample.docx"

    segments = build_segments_metadata(
        str(docx_path),
        log_func=None,
        search_providers=((fake_search, "StubTube"),),
    )

    assert len(segments) == 3
    assert segments[0]["text"].startswith("First English paragraph")
    assert segments[1]["text"].startswith("It also references")
    assert segments[2]["text"].startswith("Fourth English paragraph")
