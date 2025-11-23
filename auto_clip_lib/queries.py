"""Helpers for building search queries."""


def generate_queries(segment: dict, max_attempts: int = 3) -> list[str]:
    queries = []
    keywords = [kw for kw in segment.get("keywords", []) if kw]
    joined = " ".join(keywords).strip()
    if joined:
        queries.append(joined)
    if keywords:
        queries.extend(keywords)
    text = segment.get("text", "").strip()
    if text:
        words = text.split()
        snippet = " ".join(words[:5]).strip()
        if snippet:
            queries.append(snippet)
        queries.append(text)
    deduped = []
    seen = set()
    for q in queries:
        q = q.strip()
        if not q:
            continue
        lower = q.lower()
        if lower in seen:
            continue
        deduped.append(q)
        seen.add(lower)
        if len(deduped) >= max_attempts:
            break
    if not deduped:
        deduped.append("geopolitics")
    return deduped
