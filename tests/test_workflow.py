from __future__ import annotations

from auto_clip_lib.workflow import run_paginated_workflow


def test_run_paginated_workflow_creates_batches(fixtures_dir, fake_search, stub_llm, tmp_path):
    doc_path = fixtures_dir / "sample.docx"

    segments_page1, output_dir, metadata_path, next_index, total = run_paginated_workflow(
        str(doc_path),
        log_func=None,
        search_providers=((fake_search, "StubTube"),),
        start_index=0,
        page_size=1,
        output_prefix="test",
    )
    assert len(segments_page1) == 1
    assert next_index == 1
    assert total >= 1

    segments_page2, same_dir, same_metadata, next_index2, total2 = run_paginated_workflow(
        None,
        log_func=None,
        search_providers=((fake_search, "StubTube"),),
        start_index=next_index,
        page_size=1,
        existing_output_dir=str(output_dir),
    )
    assert str(same_dir) == str(output_dir)
    assert str(same_metadata) == str(metadata_path)
    assert len(segments_page2) == 1
    assert next_index2 == 2
    assert total2 == total
