from __future__ import annotations

from string import punctuation

from backend.models import Scenario, Skill
from backend.tools.skill_store import load_skills


def _tokens(text: str) -> set[str]:
    clean = text.lower().translate(str.maketrans("", "", punctuation))
    return {token for token in clean.split() if len(token) > 2}


def retrieve_skills(task_text: str, limit: int = 3) -> list[Skill]:
    query = _tokens(task_text)
    scored: list[tuple[int, Skill]] = []
    for skill in load_skills():
        haystack = " ".join(
            [skill.name, skill.description, skill.anti_pattern, " ".join(skill.when_to_use), " ".join(skill.tags)]
        )
        score = len(query & _tokens(haystack))
        if skill.status == "approved" and score > 0:
            scored.append((score, skill))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [skill for _, skill in scored[:limit]]


def retrieve_skills_for_scenario(scenario: Scenario, limit: int = 3) -> list[Skill]:
    query_text = f"{scenario.task}\n{scenario.input_text}\n{scenario.target_skill}\n{scenario.pair_id}"
    candidates = retrieve_skills(query_text, limit=20)
    preferred = []
    target = scenario.target_skill.lower()
    pair_terms = set(scenario.pair_id.replace("_", " ").split())
    for skill in candidates:
        skill_text = " ".join([skill.name, skill.description, " ".join(skill.tags)]).lower()
        if target in skill.name.lower() or pair_terms & _tokens(skill_text):
            preferred.append(skill)
    ordered = preferred + [skill for skill in candidates if skill not in preferred]
    return ordered[:limit]
