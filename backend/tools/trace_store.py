from __future__ import annotations

from backend.models import AttemptTrace
from backend.tools.json_store import read_json, write_json


def load_traces() -> list[AttemptTrace]:
    return [AttemptTrace(**item) for item in read_json("traces.json", [])]


def save_trace(trace: AttemptTrace) -> AttemptTrace:
    traces = [item.model_dump() for item in load_traces()]
    traces = [item for item in traces if item["trace_id"] != trace.trace_id]
    traces.append(trace.model_dump())
    write_json("traces.json", traces)
    return trace


def get_trace(trace_id: str) -> AttemptTrace:
    for trace in load_traces():
        if trace.trace_id == trace_id:
            return trace
    raise KeyError(f"Unknown trace_id: {trace_id}")
