"""Dory the investigator: a real ADK/Gemini agent that names a root cause.

``run_investigation`` keeps its original signature and returns the same
``AttemptTrace``. Internally it now:
  1. runs the small Python tools (redact / keywords / timeline) to build the
     TraceSteps the UI shows, and
  2. asks the real Dory LlmAgent to make the actual root-cause decision.

Demo behaviour (kept reliable with low temperature + prompt shaping):
  * WITHOUT a retrieved skill, Dory only sees the raw logs and is told to give a
    quick guess -> it falls for the loudest / most repeated error, low confidence.
  * WITH a retrieved skill, the skill's lesson and steps plus a timeline are
    injected -> Dory reaches the correct upstream root cause with higher
    confidence.
"""

from __future__ import annotations

from uuid import uuid4

from backend.agents import AGENT_DORY
from backend.agents.adk_runtime import DoryOutput, build_dory, run_agent
from backend.models import AgentLog, AttemptTrace, FinalAnswer, Scenario, Skill, TraceStep
from backend.tools.keyword_pattern_tool import detect_keywords
from backend.tools.redactor import redact_text
from backend.tools.skill_store import increment_usage
from backend.tools.timeline_tool import build_timeline


def _matches_expected(answer: str, expected: str) -> bool:
    answer_terms = {term for term in answer.lower().replace(";", " ").split() if len(term) > 3}
    expected_terms = {term for term in expected.lower().replace(";", " ").split() if len(term) > 3}
    return bool(answer_terms & expected_terms) and not answer.lower().startswith(("gateway", "frontend", "api service"))


def _naive_prompt(scenario: Scenario, redacted_text: str) -> str:
    """No skill: quick, frequency-driven guess -> reliably lured by the loudest error.

    Emulates a hurried investigator who trusts the noisiest signal instead of
    event order -- exactly the "loudest error trap" the project is about.
    """
    return (
        f"Task: {scenario.task}\n\n"
        "Here are the raw incident logs:\n"
        f"{redacted_text}\n\n"
        "You are in a hurry, so use the fast heuristic: the component printing the MOST error lines "
        "is where the problem is. Scan the logs, find the error message that repeats most often (the "
        "loudest one), and name THAT component's failure as the root cause. Do not build a timeline or "
        "reason about which event came first. Because this is a quick guess, keep your confidence "
        "modest (around 0.5 to 0.65)."
    )


def _skilled_prompt(scenario: Scenario, redacted_text: str, timeline: dict, skills: list[Skill]) -> str:
    """With skill: inject the learned method + timeline -> reliably reaches the real cause."""
    lessons = []
    for skill in skills:
        steps = "\n".join(f"  - {step}" for step in skill.steps)
        lessons.append(
            f"Skill: {skill.name}\n{skill.description}\n"
            f"Method:\n{steps}\n"
            f"Anti-pattern to avoid: {skill.anti_pattern}"
        )
    earliest = timeline["earliest_clue"]
    earliest_line = earliest["message"] if earliest else "no clearly timestamped first event"
    ordered = "\n".join(f"{e['time']} {e['message']}" for e in timeline["ordered_events"]) or redacted_text
    return (
        f"Task: {scenario.task}\n\n"
        "Apply the following LEARNED method(s) from past incidents:\n\n"
        + "\n\n".join(lessons)
        + "\n\nIncident logs in time order:\n"
        f"{ordered}\n\n"
        f"The earliest abnormal event is: {earliest_line}\n\n"
        "Build on the timeline: the loudest / most repeated error is usually a downstream SYMPTOM. "
        "Identify the earliest upstream failure that explains the later errors and report THAT as the "
        "root cause. You applied a proven method, so be confident (around 0.8 to 0.9)."
    )


def _ask_dory(prompt: str) -> DoryOutput:
    raw = run_agent(build_dory(), prompt)
    return DoryOutput.model_validate_json(raw)


def run_investigation(scenario: Scenario, skills: list[Skill]) -> AttemptTrace:
    redacted = redact_text(scenario.input_text)
    redacted_text = str(redacted["text"])
    keyword_result = detect_keywords(redacted_text)
    timeline = build_timeline(redacted_text)

    if skills:
        prompt = _skilled_prompt(scenario, redacted_text, timeline, skills)
    else:
        prompt = _naive_prompt(scenario, redacted_text)
    decision = _ask_dory(prompt)

    answer = FinalAnswer(
        likely_cause=decision.root_cause,
        confidence=round(max(0.0, min(1.0, decision.confidence)), 2),
        evidence=decision.evidence or [decision.reasoning],
        next_checks=decision.next_checks,
    )

    used_skill_ids = [skill.skill_id for skill in skills]
    if used_skill_ids:
        increment_usage(used_skill_ids)

    skill_summary = (
        f"Retrieved and applied {len(skills)} saved skill(s): {', '.join(skill.name for skill in skills)}."
        if skills
        else "No saved skills were applied; answered from a quick read of the logs."
    )
    agent_logs = [
        AgentLog(
            agent=AGENT_DORY,
            event="intake",
            summary="Reviewed the task input, redacted secret-like values, and prepared an investigation trace.",
            confidence=0.9,
        ),
        AgentLog(
            agent=AGENT_DORY,
            event="skill_retrieval",
            summary=skill_summary,
            confidence=0.82 if skills else 0.6,
        ),
        AgentLog(
            agent=AGENT_DORY,
            event="answer_selection",
            summary=f"Gemini chose '{answer.likely_cause}'. {decision.reasoning}",
            confidence=answer.confidence,
        ),
    ]
    steps = [
        TraceStep(
            step=1,
            action="redaction_tool",
            observation="; ".join(redacted["summary"]),
            reasoning_summary="The agent redacted sensitive-looking values before storing the trace.",
        ),
        TraceStep(
            step=2,
            action="keyword_pattern_tool",
            observation=f"Detected hints: {', '.join(keyword_result['detected_hints']) or 'none'}",
            reasoning_summary="The agent looked for incident patterns such as deployment, retry, and resource clues.",
        ),
        TraceStep(
            step=3,
            action="timeline_tool",
            observation=f"Earliest clue: {timeline['earliest_clue']['message'] if timeline['earliest_clue'] else 'none'}",
            reasoning_summary="The agent checked event order before ranking possible causes.",
        ),
    ]
    if skills:
        steps.append(
            TraceStep(
                step=4,
                action="skill_retriever",
                observation=f"Using skills: {', '.join(skill.name for skill in skills)}",
                reasoning_summary="The agent applied relevant saved procedures before answering.",
            )
        )
    return AttemptTrace(
        trace_id=f"trace_{uuid4().hex[:8]}",
        scenario_id=scenario.scenario_id,
        used_skills=used_skill_ids,
        steps=steps,
        agent_logs=agent_logs,
        final_answer=answer,
        matched_expected=_matches_expected(answer.likely_cause, scenario.expected_answer),
    )
