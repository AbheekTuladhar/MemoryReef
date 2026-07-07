"""Real Google ADK agents for MemoryReef: Dory, Nemo, and Puffer.

Each of the three reef characters is a genuine :class:`LlmAgent` backed by
Gemini. They do NOT use ADK tools (we run the small Python tools ourselves and
feed their output into the prompt) because ``output_schema`` + ``tools`` is not
reliably supported on Gemini 2.x, and structured JSON output is what keeps the
investigate -> reflect -> verify loop parseable.

The single LLM boundary is :func:`run_agent`. Every agent call in the product
goes through it, so a test can monkeypatch ``run_agent`` to return canned JSON
without any config flag or deterministic fallback in the real path.
"""

from __future__ import annotations

import asyncio

from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from google.genai import types
from pydantic import BaseModel, Field

from backend.agents import AGENT_DORY, AGENT_NEMO, AGENT_PUFFER
from backend.config import MODEL

_APP_NAME = "memoryreef"

# Low temperature keeps the wrong->right demo deterministic across takes.
_DETERMINISTIC = types.GenerateContentConfig(temperature=0.1)


# --- Structured output schemas -------------------------------------------------
# Kept small and flat so parsing with ``Model.model_validate_json`` is robust.


class DoryOutput(BaseModel):
    """Root-cause decision produced by Dory the investigator."""

    root_cause: str = Field(description="One-line likely root cause of the incident.")
    confidence: float = Field(description="Confidence between 0 and 1.")
    reasoning: str = Field(description="Short justification for the chosen cause.")
    evidence: list[str] = Field(default_factory=list, description="Log lines or facts that support the cause.")
    next_checks: list[str] = Field(default_factory=list, description="Concrete next things to verify.")


class ProposedSkill(BaseModel):
    """A reusable debugging lesson proposed by Nemo."""

    name: str
    description: str
    when_to_use: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    anti_pattern: str = ""
    tags: list[str] = Field(default_factory=list)


class NemoOutput(BaseModel):
    """Reflection produced by Nemo after reviewing a trace."""

    reflection_summary: str
    lesson: str
    skill: ProposedSkill


class PufferOutput(BaseModel):
    """Verdict produced by Puffer the verifier."""

    status: str = Field(description="One of: approved, revised, rejected.")
    reason: str
    revised_fields: dict[str, str] = Field(default_factory=dict)


# --- Agent factories -----------------------------------------------------------
# Instructions carry the persona + fixed rules; the per-run specifics (logs,
# retrieved skill, trace) travel in the prompt passed to ``run_agent``.

DORY_INSTRUCTION = (
    "You are Dory, a fast incident investigator. You read short service logs and name the single "
    "most likely ROOT CAUSE of the incident. Follow the guidance in the user's message exactly: "
    "when you are told to give a quick guess, answer fast from the surface of the logs and keep "
    "confidence modest; when you are given a learned method, apply it faithfully and be more "
    "confident. Return only the structured fields."
)

NEMO_INSTRUCTION = (
    "You are Nemo, a reflective learner. You review a debugging trace and distill ONE reusable, "
    "general debugging skill (not tied to the specific service names) that would help next time. "
    "The skill must be procedural and safe to store: never include secrets, tokens, emails, or raw "
    "private data. Prefer the lesson name the user suggests. Return only the structured fields."
)

PUFFER_INSTRUCTION = (
    "You are Puffer, a strict but fair skill verifier (a reef gatekeeper). You decide whether a "
    "proposed debugging skill should be stored in the shared library. Approve skills that are "
    "general, actionable, procedural, and safe. Use 'revised' if it is close but needs a small fix, "
    "and 'rejected' only if it is unsafe, secret-bearing, or not reusable. Mechanical safety checks "
    "(secrets, duplicates, too-terse) are handled outside you; focus on usefulness and generality. "
    "Return only the structured fields."
)


def build_dory() -> LlmAgent:
    return LlmAgent(
        name=AGENT_DORY,
        model=MODEL,
        description="Fast incident investigator that names the likely root cause.",
        instruction=DORY_INSTRUCTION,
        output_schema=DoryOutput,
        generate_content_config=_DETERMINISTIC,
    )


def build_nemo() -> LlmAgent:
    return LlmAgent(
        name=AGENT_NEMO,
        model=MODEL,
        description="Reflective learner that distills reusable debugging skills.",
        instruction=NEMO_INSTRUCTION,
        output_schema=NemoOutput,
        generate_content_config=_DETERMINISTIC,
    )


def build_puffer() -> LlmAgent:
    return LlmAgent(
        name=AGENT_PUFFER,
        model=MODEL,
        description="Strict verifier that approves, revises, or rejects proposed skills.",
        instruction=PUFFER_INSTRUCTION,
        output_schema=PufferOutput,
        generate_content_config=_DETERMINISTIC,
    )


# --- The single LLM boundary ---------------------------------------------------


def run_agent(agent: LlmAgent, prompt: str) -> str:
    """Run an ADK ``LlmAgent`` once and return its final response text (JSON).

    This is the ONE seam every agent call goes through. Tests monkeypatch this
    function to return canned JSON keyed off ``agent.name``; the product path
    always hits the real Gemini backend (no fallback).
    """

    runner = InMemoryRunner(agent=agent, app_name=_APP_NAME)
    user_id = "memoryreef-user"
    # create_session is async; endpoints run in a threadpool (sync def), so there
    # is no running loop and asyncio.run is safe here.
    session = asyncio.run(
        runner.session_service.create_session(app_name=_APP_NAME, user_id=user_id)
    )
    message = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])

    final_text = ""
    for event in runner.run(user_id=user_id, session_id=session.id, new_message=message):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = event.content.parts[0].text or ""
    return final_text
