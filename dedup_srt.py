import argparse
from pathlib import Path

import pysrt


def _normalize(text: str) -> str:
    """Collapse whitespace/newlines to detect duplicate captions."""
    return " ".join((text or "").replace("\n", " ").split())


def _join(tokens):
    return " ".join(tokens)


def _longest_overlap(prev_tokens, curr_tokens):
    max_len = min(len(prev_tokens), len(curr_tokens))
    for size in range(max_len, 0, -1):
        if prev_tokens[-size:] == curr_tokens[:size]:
            return size
    return 0


def deduplicate_subtitles(subs: pysrt.SubRipFile) -> pysrt.SubRipFile:
    """Emit only the new words that appear in each rolling caption update."""
    cleaned_items = []
    prev_tokens = []
    for sub in subs:
        normalized = _normalize(sub.text)
        if not normalized:
            continue
        current_tokens = normalized.split()
        if not current_tokens:
            continue
        new_tokens = current_tokens
        if prev_tokens:
            overlap = _longest_overlap(prev_tokens, current_tokens)
            if overlap == len(current_tokens):
                prev_tokens = current_tokens
                continue
            if overlap > 0:
                new_tokens = current_tokens[overlap:]
        text = _join(new_tokens).strip()
        if not text:
            prev_tokens = current_tokens
            continue
        item = pysrt.SubRipItem(
            index=sub.index,
            start=pysrt.SubRipTime(milliseconds=sub.start.ordinal),
            end=pysrt.SubRipTime(milliseconds=sub.end.ordinal),
            text=text,
        )
        cleaned_items.append(item)
        prev_tokens = current_tokens
    cleaned = pysrt.SubRipFile(items=cleaned_items)
    cleaned.clean_indexes()
    return cleaned


def main():
    parser = argparse.ArgumentParser(
        description="Deduplicate auto-generated SRT captions while preserving timing."
    )
    parser.add_argument("input", type=Path, help="Path to the noisy SRT file.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Optional output path (defaults to <input>.dedup.srt).",
    )
    args = parser.parse_args()
    if not args.input.exists():
        parser.error(f"SRT file not found: {args.input}")
    subs = pysrt.open(str(args.input))
    cleaned = deduplicate_subtitles(subs)
    out_path = args.output or args.input.with_suffix(".dedup.srt")
    cleaned.save(str(out_path), encoding="utf-8")
    print(f"Clean captions written to {out_path}")


if __name__ == "__main__":
    main()
