"""Puffer the verifier: a real ADK/Gemini agent that judges proposed skills.

``verify_skill`` keeps its original signature and returns a ``Verification``.
Mechanical safety checks stay as hard Python guards (they must never depend on
an LLM): secret/PII rejection, too-terse revision, and duplicate detection. Only
skills that clear those guards are handed to the Puffer LlmAgent, which makes the
nuanced usefulness/generality judgement.
"""

from __future__ import annotations

import re

from backend.agents import AGENT_PUFFER
from backend.agents.adk_runtime import PufferOutput, build_puffer, run_agent
from backend.models import AgentLog, Skill, Verification
from backend.tools.skill_store import load_skills


SECRETISH = re.compile(r"(@|password|passwd|api[_-]?key|token=|secret=|[A-Za-z0-9_-]{32,})", re.I)


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "skill"


def _tag_key(skill: Skill) -> tuple[str, str, str]:
    tags = [tag.lower().strip() for tag in skill.tags[-3:]]
    while len(tags) < 3:
        tags.append("")
    return tuple(tags[:3])


def _log(event: str, summary: str, confidence: float) -> AgentLog:
    return AgentLog(agent=AGENT_PUFFER, event=event, summary=summary, confidence=confidence)


def _ask_puffer(skill: Skill) -> PufferOutput:
    steps = "\n".join(f"  - {step}" for step in skill.steps)
    prompt = (
        "Review this proposed debugging skill for the shared library.\n\n"
        f"Name: {skill.name}\n"
        f"Description: {skill.description}\n"
        f"When to use: {'; '.join(skill.when_to_use)}\n"
        f"Steps:\n{steps}\n"
        f"Anti-pattern: {skill.anti_pattern}\n"
        f"Tags: {', '.join(skill.tags)}\n\n"
        "Decide status = approved / revised / rejected. Approve if it is a general, actionable, "
        "reusable debugging procedure. Use 'revised' with concrete revised_fields only if a small fix "
        "would make it storable. Reject only if it is not reusable or clearly unsafe."
    )
    return PufferOutput.model_validate_json(run_agent(build_puffer(), prompt))


def verify_skill(skill: Skill) -> Verification:
    existing = load_skills()
    existing_tag_keys = {_tag_key(item) for item in existing}
    combined = " ".join([skill.name, skill.description, " ".join(skill.steps), " ".join(skill.when_to_use)])
    review_log = _log(
        "skill_review",
        f"Checked proposed skill '{skill.name}' for usefulness, generality, duplicate tags, and secret-like content.",
        0.82,
    )

    # --- Hard, deterministic safety guards (never delegated to the LLM) --------
    if SECRETISH.search(combined):
        return Verification(
            status="rejected",
            reason="The skill appears to contain private or secret-like data.",
            final_skill=None,
            confidence=0.9,
            agent_logs=[review_log, _log("decision", "Rejected: matched secret-like or private-data patterns.", 0.9)],
        )
    if len(skill.description.split()) < 8 or len(skill.steps) < 3:
        revised = skill.model_copy(update={"status": "revised"})
        return Verification(
            status="revised",
            reason="The skill was too terse, but can be revised before saving.",
            final_skill=revised,
            confidence=0.74,
            agent_logs=[review_log, _log("decision", "Revised: needed more actionable detail.", 0.74)],
        )
    if _tag_key(skill) in existing_tag_keys:
        return Verification(
            status="rejected",
            reason=(
                "A similar skill already exists with the same final three keywords. "
                "Run reflection again to generate a different lesson."
            ),
            final_skill=None,
            confidence=0.9,
            agent_logs=[review_log, _log("decision", f"Rejected duplicate tag signature: {', '.join(skill.tags[-3:])}.", 0.9)],
        )

    # --- Nuanced judgement by the real Puffer agent ----------------------------
    verdict = _ask_puffer(skill)
    status = verdict.status.strip().lower()

    if status == "rejected":
        return Verification(
            status="rejected",
            reason=verdict.reason,
            final_skill=None,
            confidence=0.85,
            agent_logs=[review_log, _log("decision", f"Puffer rejected the skill: {verdict.reason}", 0.85)],
        )
    if status == "revised":
        # Only allow Puffer to revise plain string fields, so we never inject a
        # string where the schema expects a list.
        allowed = {"name", "description", "anti_pattern"}
        safe_fields = {k: v for k, v in verdict.revised_fields.items() if k in allowed and isinstance(v, str)}
        revised = skill.model_copy(update={**safe_fields, "status": "revised"})
        return Verification(
            status="revised",
            reason=verdict.reason,
            final_skill=revised,
            confidence=0.8,
            agent_logs=[review_log, _log("decision", f"Puffer revised the skill: {verdict.reason}", 0.8)],
        )
    # Default to approval for anything Puffer did not explicitly reject/revise.
    final_skill = skill.model_copy(update={"status": "approved"})
    return Verification(
        status="approved",
        reason=verdict.reason or "The skill is general, actionable, non-duplicative, and safe to store.",
        final_skill=final_skill,
        confidence=0.88,
        agent_logs=[review_log, _log("decision", f"Puffer approved the skill: {verdict.reason}", 0.88)],
    )
