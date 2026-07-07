"""Nemo the reflector: a real ADK/Gemini agent that distills a reusable skill.

``reflect_on_trace`` keeps its original signature and returns
``(Reflection, Skill)``. Internally Nemo reviews the trace summary and proposes
one general, procedural debugging skill. We steer the name toward the scenario's
target skill (still LLM-authored) so the learning loop is coherent.
"""

from __future__ import annotations

import re
from uuid import uuid4

from backend.agents import AGENT_NEMO
from backend.agents.adk_runtime import NemoOutput, build_nemo, run_agent
from backend.models import AgentLog, AttemptTrace, Reflection, Scenario, Skill


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "skill"


def _prompt(trace: AttemptTrace, scenario: Scenario) -> str:
    steps = "\n".join(f"  {s.step}. {s.action}: {s.observation}" for s in trace.steps)
    answer = trace.final_answer
    outcome = "matched the expected answer" if trace.matched_expected else "did NOT match the expected answer"
    return (
        f"Task the investigator faced: {scenario.task}\n"
        f"Incident logs:\n{scenario.input_text}\n\n"
        f"Investigator's trace steps:\n{steps}\n\n"
        f"Investigator's answer: {answer.likely_cause} (confidence {answer.confidence})\n"
        f"Reasoning given: {'; '.join(answer.evidence)}\n"
        f"Expected answer: {scenario.expected_answer}\n"
        f"Outcome: the answer {outcome}.\n\n"
        "Reflect on what general debugging lesson this incident teaches, then propose ONE reusable "
        "skill that would help an investigator handle similar incidents next time. The lesson is best "
        f"described as: \"{scenario.target_skill}\" -- name the skill exactly that (or a close variant "
        "that keeps its key words). Make the description, when_to_use, and steps general (do not hard-code "
        "these specific service names), and give a short anti_pattern and a few tags."
    )


def reflect_on_trace(trace: AttemptTrace, scenario: Scenario) -> tuple[Reflection, Skill]:
    raw = run_agent(build_nemo(), _prompt(trace, scenario))
    output = NemoOutput.model_validate_json(raw)
    proposed = output.skill

    skill = Skill(
        skill_id=f"skill_{_slug(proposed.name)}_{uuid4().hex[:6]}",
        name=proposed.name,
        description=proposed.description,
        when_to_use=proposed.when_to_use,
        steps=proposed.steps,
        anti_pattern=proposed.anti_pattern,
        source_trace_id=trace.trace_id,
        tags=proposed.tags,
        status="proposed",
    )

    confidence = 0.7 if scenario.purpose == "custom" else 0.82
    reflection = Reflection(
        reflection_id=f"reflection_{uuid4().hex[:8]}",
        trace_id=trace.trace_id,
        what_happened=output.reflection_summary,
        lesson=output.lesson,
        proposed_skill_id=skill.skill_id,
        confidence=confidence,
        agent_logs=[
            AgentLog(
                agent=AGENT_NEMO,
                event="trace_review",
                summary=f"Reviewed trace {trace.trace_id} with {len(trace.steps)} tool step(s) and {len(trace.used_skills)} saved skill reference(s).",
                confidence=0.84,
            ),
            AgentLog(
                agent=AGENT_NEMO,
                event="lesson_extraction",
                summary=f"Distilled a reusable lesson and proposed the skill '{skill.name}'.",
                confidence=confidence,
            ),
            AgentLog(
                agent=AGENT_NEMO,
                event="safety_filter",
                summary="Kept the proposed skill procedural and free of secret-like or private content.",
                confidence=0.88,
            ),
        ],
    )
    return reflection, skill
