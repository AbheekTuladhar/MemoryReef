"""Shared test fixtures.

The e2e test exercises the real FastAPI loop, but we mock the ONE LLM boundary
(``adk_runtime.run_agent``) so the test is fast, offline, deterministic, and
free — no Vertex/Gemini calls, no credentials, no token cost. Everything else
(endpoints, stores, retrieval, Puffer's Python safety guards, the models) runs
for real, so this still verifies the whole loop wiring end to end.

Each agent is a real ``LlmAgent`` whose ``.name`` is Dory / Nemo / Puffer; the
fake keys off that name and returns JSON matching each agent's ``output_schema``.
Dory additionally branches on the prompt: the "skilled" prompt injects a
"LEARNED method", which is our signal to return the correct upstream cause.
"""

from __future__ import annotations

import json

import pytest

from backend.agents import AGENT_DORY, AGENT_NEMO, AGENT_PUFFER

# Dory WITHOUT a skill: lured by the loudest/most-repeated error -> wrong, modest confidence.
_DORY_WRONG = json.dumps(
    {
        "root_cause": "Frontend service failure indicated by repeated 503 errors",
        "confidence": 0.6,
        "reasoning": "The frontend printed the most error lines, so it looks like the culprit.",
        "evidence": ["frontend ERROR 503", "frontend ERROR 503", "frontend ERROR 503"],
        "next_checks": ["Check the frontend service health and resource use"],
    }
)

# Dory WITH the learned skill: follows the timeline to the earliest upstream cause -> right, confident.
_DORY_RIGHT = json.dumps(
    {
        "root_cause": "Redis reached its maxmemory limit, triggering a cascade failure",
        "confidence": 0.85,
        "reasoning": "The earliest event is Redis maxmemory; the later API and frontend errors are downstream symptoms.",
        "evidence": ["redis ERROR maxmemory limit reached", "api ERROR connection refused"],
        "next_checks": ["Verify Redis memory usage and maxmemory setting", "Check the Redis eviction policy"],
    }
)

# Nemo: distills the reusable, service-agnostic lesson (>=8-word description, >=3 steps, 3 tags
# so it clears Puffer's deterministic guards).
_NEMO = json.dumps(
    {
        "reflection_summary": "The investigator trusted the loudest, most repeated error instead of checking event order.",
        "lesson": "Build a timeline first; the loudest error is usually a downstream symptom, not the cause.",
        "skill": {
            "name": "Avoid the Loudest Error Trap",
            "description": "Before naming a root cause, order the events by time and trace the earliest upstream failure instead of the most frequent error.",
            "when_to_use": [
                "Logs show many repeated errors from one component",
                "An incident has cascading failures across services",
            ],
            "steps": [
                "Collect and timestamp every error line",
                "Sort the events in chronological order",
                "Find the earliest abnormal event",
                "Report that earliest upstream failure as the root cause",
            ],
            "anti_pattern": "Blaming the component that prints the most error lines.",
            "tags": ["timeline", "root-cause", "cascading-failure"],
        },
    }
)

# Puffer: the skill is general, actionable, and safe -> approve.
_PUFFER = json.dumps(
    {"status": "approved", "reason": "General, actionable, procedural, and safe to store.", "revised_fields": {}}
)


def _fake_run_agent(agent, prompt: str) -> str:
    """Stand-in for ``adk_runtime.run_agent`` — returns canned JSON, no network."""
    if agent.name == AGENT_DORY:
        # The skilled prompt injects a learned method; that's our wrong->right switch.
        return _DORY_RIGHT if "LEARNED method" in prompt else _DORY_WRONG
    if agent.name == AGENT_NEMO:
        return _NEMO
    if agent.name == AGENT_PUFFER:
        return _PUFFER
    raise AssertionError(f"unexpected agent in test: {agent.name!r}")


@pytest.fixture(autouse=True)
def mock_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch the LLM boundary in every module that imported it. Autouse: every
    test in this package runs fully offline."""
    for module in ("dory", "nemo", "puffer"):
        monkeypatch.setattr(f"backend.agents.{module}.run_agent", _fake_run_agent)
