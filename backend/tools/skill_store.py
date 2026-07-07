from __future__ import annotations

import re

from backend.models import Skill
from backend.tools.json_store import read_json, write_json


def load_skills() -> list[Skill]:
    return [Skill(**item) for item in read_json("skills.json", [])]


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


def save_skill(skill: Skill) -> Skill:
    current = load_skills()
    existing = next((item for item in current if item.skill_id == skill.skill_id), None)
    duplicate_name = next(
        (item for item in current if item.name.lower() == skill.name.lower() and item.skill_id != skill.skill_id),
        None,
    )
    if duplicate_name:
        unique_name = _unique_name(skill.name, {item.name.lower() for item in current})
        skill = skill.model_copy(update={"skill_id": f"skill_{_slug(unique_name)}", "name": unique_name})
    if existing and skill.usage_count == 0:
        skill = skill.model_copy(update={"usage_count": existing.usage_count})
    skills = [item.model_dump() for item in current if item.skill_id != skill.skill_id]
    skills.append(skill.model_dump())
    write_json("skills.json", skills)
    return skill


def increment_usage(skill_ids: list[str]) -> None:
    skills = load_skills()
    changed = False
    for skill in skills:
        if skill.skill_id in skill_ids:
            skill.usage_count += 1
            changed = True
    if changed:
        write_json("skills.json", [skill.model_dump() for skill in skills])
