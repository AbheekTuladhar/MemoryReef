from __future__ import annotations

import re


TIME_RE = re.compile(r"^(?P<time>\d{2}:\d{2})\s+(?P<message>.+)$")


def build_timeline(text: str) -> dict[str, object]:
    events = []
    for line in text.splitlines():
        match = TIME_RE.match(line.strip())
        if match:
            events.append({"time": match.group("time"), "message": match.group("message")})
    events.sort(key=lambda item: item["time"])
    earliest = events[0] if events else None
    later = events[1:] if len(events) > 1 else []
    return {
        "ordered_events": events,
        "earliest_clue": earliest,
        "later_symptoms": later,
    }
