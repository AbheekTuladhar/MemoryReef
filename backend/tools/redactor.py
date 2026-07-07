from __future__ import annotations

import re


PATTERNS = [
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "[REDACTED_EMAIL]"),
    (re.compile(r"(?i)(password|passwd|pwd|token|api[_-]?key|secret)=\S+"), r"\1=[REDACTED_SECRET]"),
    (re.compile(r"\b[A-Za-z0-9_-]{32,}\b"), "[REDACTED_TOKEN]"),
]


def redact_text(text: str) -> dict[str, object]:
    redacted = text
    summary: list[str] = []
    for pattern, replacement in PATTERNS:
        redacted, count = pattern.subn(replacement, redacted)
        if count:
            summary.append(f"Redacted {count} occurrence(s) matching {pattern.pattern}")
    return {"text": redacted, "summary": summary or ["No sensitive patterns detected."]}
