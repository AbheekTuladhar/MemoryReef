from __future__ import annotations


PATTERN_TAGS = {
    "deployment": ["deploy", "version", "feature flag", "env var", "config", "secret"],
    "retry": ["retry", "attempt", "backlog", "queue", "rate limit"],
    "database": ["db", "database", "connection"],
    "gateway": ["gateway", "502", "503", "504", "500", "401"],
    "memory": ["memory", "maxmemory"],
    "missing_config": ["missing env", "unknown feature flag", "secret"],
    "ambiguous": ["timeout", "authentication failed", "failed request"],
}


def detect_keywords(text: str) -> dict[str, object]:
    lowered = text.lower()
    detected = []
    for tag, terms in PATTERN_TAGS.items():
        if any(term in lowered for term in terms):
            detected.append(tag)
    return {"detected_hints": detected}
