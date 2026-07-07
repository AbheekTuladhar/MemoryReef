from __future__ import annotations

import re

from backend.models import AgentLog, Skill, Verification
from backend.tools.skill_store import load_skills


SECRETISH = re.compile(r"(@|password|passwd|api[_-]?key|token=|secret=|[A-Za-z0-9_-]{32,})", re.I)


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "skill"


def _unique_name(base_name: str, existing_names: set[str]) -> str:
    if base_name.lower() not in existing_names:
        return base_name
    suffix = 2
    while f"{base_name} {suffix}".lower() in existing_names:
        suffix += 1
    return f"{base_name} {suffix}"


def _tag_key(skill: Skill) -> tuple[str, str, str]:
    tags = [tag.lower().strip() for tag in skill.tags[-3:]]
    while len(tags) < 3:
        tags.append("")
    return tuple(tags[:3])


def verify_skill(skill: Skill) -> Verification:
    existing = load_skills()
    existing_names = {item.name.lower() for item in existing}
    existing_tag_keys = {_tag_key(item) for item in existing}
    combined = " ".join([skill.name, skill.description, " ".join(skill.steps), " ".join(skill.when_to_use)])
    base_logs = [
        AgentLog(
            agent="Verifier Agent",
            event="skill_review",
            summary=f"Checked proposed skill '{skill.name}' for usefulness, generality, duplicate names, and secret-like content.",
            confidence=0.82,
        )
    ]
    if SECRETISH.search(combined):
        return Verification(
            status="rejected",
            reason="The skill appears to contain private or secret-like data.",
            final_skill=None,
            confidence=0.9,
            agent_logs=base_logs
            + [
                AgentLog(
                    agent="Verifier Agent",
                    event="decision",
                    summary="Rejected the skill because it matched secret-like or private-data patterns.",
                    confidence=0.9,
                )
            ],
        )
    if len(skill.description.split()) < 8 or len(skill.steps) < 3:
        revised = skill.model_copy(update={"status": "revised"})
        return Verification(
            status="revised",
            reason="The skill was too terse, but can be revised before saving.",
            final_skill=revised,
            confidence=0.74,
            agent_logs=base_logs
            + [
                AgentLog(
                    agent="Verifier Agent",
                    event="decision",
                    summary="Revised instead of approving directly because the skill needed more actionable detail.",
                    confidence=0.74,
                )
            ],
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
            agent_logs=base_logs
            + [
                AgentLog(
                    agent="Verifier Agent",
                    event="decision",
                    summary=f"Rejected duplicate tag signature: {', '.join(skill.tags[-3:])}.",
                    confidence=0.9,
                )
            ],
        )
    unique_name = _unique_name(skill.name, existing_names)
    if unique_name != skill.name:
        revised = skill.model_copy(
            update={
                "skill_id": f"skill_{_slug(unique_name)}",
                "name": unique_name,
                "status": "revised",
            }
        )
        return Verification(
            status="revised",
            reason=f"A skill named '{skill.name}' already exists, so the proposed skill was renamed to '{unique_name}'.",
            final_skill=revised,
            confidence=0.86,
            agent_logs=base_logs
            + [
                AgentLog(
                    agent="Verifier Agent",
                    event="decision",
                    summary=f"Renamed the skill to '{unique_name}' to avoid a duplicate library entry.",
                    confidence=0.86,
                )
            ],
        )
    final_skill = skill.model_copy(update={"status": "approved"})
    return Verification(
        status="approved",
        reason="The skill is general, actionable, non-duplicative, and safe to store.",
        final_skill=final_skill,
        confidence=0.88,
        agent_logs=base_logs
        + [
            AgentLog(
                agent="Verifier Agent",
                event="decision",
                summary="Approved the skill because it is procedural, reusable, non-duplicative, and free of secret-like content.",
                confidence=0.88,
            )
        ],
    )
