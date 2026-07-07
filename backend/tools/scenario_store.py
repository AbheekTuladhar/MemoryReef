from __future__ import annotations

from uuid import uuid4

from backend.models import Scenario
from backend.tools.json_store import read_json, write_json


def load_scenarios() -> list[Scenario]:
    base = [Scenario(**item) for item in read_json("scenarios.json", [])]
    custom = [Scenario(**item) for item in read_json("custom_scenarios.json", [])]
    return base + custom


def save_custom_scenario(
    title: str,
    task: str,
    input_text: str,
    expected_answer: str,
    target_skill: str,
) -> Scenario:
    scenario = Scenario(
        scenario_id=f"custom_{uuid4().hex[:8]}",
        title=title.strip() or "Custom Logs",
        pair_id="custom",
        purpose="custom",
        task=task.strip() or "Find the likely cause or next debugging step from these logs.",
        input_text=input_text,
        expected_answer=expected_answer.strip() or "User-provided scenario; no expected answer supplied",
        common_mistake="Overclaiming from user-provided logs without enough supporting evidence.",
        target_skill=target_skill.strip() or "Custom Debugging Lesson",
        paired_scenario_id=None,
    )
    custom = read_json("custom_scenarios.json", [])
    custom.append(scenario.model_dump())
    write_json("custom_scenarios.json", custom)
    return scenario


def get_scenario(scenario_id: str) -> Scenario:
    for scenario in load_scenarios():
        if scenario.scenario_id == scenario_id:
            return scenario
    raise KeyError(f"Unknown scenario_id: {scenario_id}")
