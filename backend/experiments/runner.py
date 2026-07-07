from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from backend.agents.dory import run_investigation
from backend.agents.nemo import reflect_on_trace
from backend.agents.puffer import verify_skill
from backend.experiments.metrics import calculate_metric_summary
from backend.experiments.persistence import save_experiment_artifacts
from backend.models import (
    AgentLog,
    ExperimentConditionResult,
    ExperimentRequest,
    ExperimentRun,
    ExperimentScenarioResult,
    Skill,
)
from backend.tools.json_store import read_json, write_json
from backend.tools.scenario_store import get_scenario
from backend.tools.skill_retriever import retrieve_skills_for_scenario
from backend.tools.skill_store import load_skills, save_skill
from backend.tools.trace_store import save_trace


DEFAULT_CONDITIONS = ["baseline", "learning", "reuse", "random_skill"]


def load_experiment_config() -> dict:
    return read_json("experiment_config.json", {})


def _condition_enabled(condition_id: str, request: ExperimentRequest) -> bool:
    requested = request.conditions or DEFAULT_CONDITIONS
    if condition_id == "random_skill" and not request.random_skill_control_enabled:
        return False
    return condition_id in requested


def _selected_pairs(config: dict, request: ExperimentRequest) -> list[dict]:
    pairs = config.get("scenario_pairs", [])
    if not request.scenario_pair_ids:
        return pairs
    wanted = set(request.scenario_pair_ids)
    return [pair for pair in pairs if pair["pair_id"] in wanted]


def _skills_for_reuse(test_scenario, enabled: bool) -> list[Skill]:
    if not enabled:
        return []
    return retrieve_skills_for_scenario(test_scenario)


def _random_skill_for_control(target_pair_id: str) -> list[Skill]:
    for skill in load_skills():
        skill_text = " ".join([skill.name, skill.description, " ".join(skill.tags)]).lower()
        if target_pair_id.replace("_", " ") not in skill_text:
            return [skill]
    return [
        Skill(
            skill_id="skill_random_control_placeholder",
            name="Random Control Skill",
            description="A deliberately unrelated generic debugging reminder used as a control condition.",
            when_to_use=["Control condition only"],
            steps=[
                "Read the task carefully.",
                "List visible evidence.",
                "Avoid using this as a domain-specific debugging skill.",
            ],
            anti_pattern="Treating the control skill as relevant incident knowledge.",
            tags=["control", "unrelated", "placebo"],
            status="approved",
        )
    ]


def _result_from_trace(condition_id: str, trace, extra_logs: list[AgentLog] | None = None) -> ExperimentConditionResult:
    logs = list(trace.agent_logs)
    if extra_logs:
        logs.extend(extra_logs)
    return ExperimentConditionResult(
        condition_id=condition_id,
        answer=trace.final_answer,
        matched_expected=trace.matched_expected,
        skills_used=trace.used_skills,
        trace_id=trace.trace_id,
        agent_logs=logs,
    )


def _learning_result(pair: dict, request: ExperimentRequest) -> tuple[ExperimentConditionResult, list[str], int]:
    learn_scenario = get_scenario(pair["learn_scenario_id"])
    trace = save_trace(run_investigation(learn_scenario, []))

    if not request.reflection_enabled:
        return _result_from_trace("learning", trace), [], 0

    reflection, proposed_skill = reflect_on_trace(trace, learn_scenario)
    saved_skill_ids: list[str] = []
    duplicate_rejections = 0
    verification_status = "not_run"
    logs = list(reflection.agent_logs)

    final_skill = proposed_skill
    if request.verifier_enabled:
        verification = verify_skill(proposed_skill)
        verification_status = verification.status
        logs.extend(verification.agent_logs)
        if verification.status == "rejected":
            duplicate_rejections = 1 if "final three" in verification.reason.lower() else 0
            final_skill = None
        else:
            final_skill = verification.final_skill or proposed_skill
    else:
        verification_status = "skipped"

    if final_skill is not None:
        saved = save_skill(final_skill.model_copy(update={"status": "approved"}))
        saved_skill_ids.append(saved.skill_id)

    result = _result_from_trace("learning", trace, logs)
    result.reflection_id = reflection.reflection_id
    result.verification_status = verification_status
    return result, saved_skill_ids, duplicate_rejections


def _run_pair(pair: dict, request: ExperimentRequest) -> ExperimentScenarioResult:
    test_scenario = get_scenario(pair["test_scenario_id"])
    condition_results: list[ExperimentConditionResult] = []
    learned_skill_ids: list[str] = []
    duplicate_rejections = 0

    baseline_result = None
    reuse_result = None

    if _condition_enabled("baseline", request):
        baseline_trace = save_trace(run_investigation(test_scenario, []))
        baseline_result = _result_from_trace("baseline", baseline_trace)
        condition_results.append(baseline_result)

    if _condition_enabled("learning", request):
        learning_result, saved_ids, rejections = _learning_result(pair, request)
        learned_skill_ids.extend(saved_ids)
        duplicate_rejections += rejections
        condition_results.append(learning_result)

    if _condition_enabled("reuse", request):
        skills = _skills_for_reuse(test_scenario, request.skill_retrieval_enabled)
        reuse_trace = save_trace(run_investigation(test_scenario, skills))
        reuse_result = _result_from_trace("reuse", reuse_trace)
        condition_results.append(reuse_result)

    if _condition_enabled("random_skill", request):
        random_skills = _random_skill_for_control(pair["pair_id"])
        random_trace = save_trace(run_investigation(test_scenario, random_skills))
        condition_results.append(_result_from_trace("random_skill", random_trace))

    improvement = bool(baseline_result and reuse_result and (not baseline_result.matched_expected) and reuse_result.matched_expected)
    notes = []
    if duplicate_rejections:
        notes.append(f"{duplicate_rejections} duplicate skill proposal(s) rejected.")

    return ExperimentScenarioResult(
        pair_id=pair["pair_id"],
        learn_scenario_id=pair["learn_scenario_id"],
        test_scenario_id=pair["test_scenario_id"],
        target_skill=pair["target_skill"],
        condition_results=condition_results,
        learned_skill_ids=learned_skill_ids,
        improvement_detected=improvement,
        notes=notes,
    )


def run_experiment(request: ExperimentRequest | None = None) -> ExperimentRun:
    request = request or ExperimentRequest()
    config = load_experiment_config()
    skill_snapshot = [skill.model_dump() for skill in load_skills()]

    try:
        write_json("skills.json", [])
        selected_pairs = _selected_pairs(config, request)
        scenario_results = [_run_pair(pair, request) for pair in selected_pairs]
        metric_summary = calculate_metric_summary(scenario_results, config)
        skill_count_after_run = len(load_skills())
        run = ExperimentRun(
            run_id=f"experiment_{uuid4().hex[:10]}",
            config_id=config.get("experiment_id", request.config_id),
            hypothesis=config.get("hypothesis", ""),
            created_at=datetime.now(UTC).isoformat(),
            request=request,
            scenario_results=scenario_results,
            metric_summary=metric_summary,
            ablation_flags={
                "verifier_enabled": request.verifier_enabled,
                "reflection_enabled": request.reflection_enabled,
                "skill_retrieval_enabled": request.skill_retrieval_enabled,
                "duplicate_filtering_enabled": request.duplicate_filtering_enabled,
                "random_skill_control_enabled": request.random_skill_control_enabled,
                "persist_experiment_skills_to_main_library": request.persist_experiment_skills_to_main_library,
            },
            reproducibility={
                **config.get("reproducibility", {}),
                "app_version": "0.1.0",
                "config_used": config.get("experiment_id", request.config_id),
                "run_id": "",
                "timestamp": "",
                "scenario_pair_count": len(selected_pairs),
                "skill_library_snapshotted": True,
                "skill_count_before_run": len(skill_snapshot),
                "skill_count_after_run": skill_count_after_run,
                "skills_restored_after_run": not request.persist_experiment_skills_to_main_library,
            },
        )
        run.reproducibility["run_id"] = run.run_id
        run.reproducibility["timestamp"] = run.created_at
        save_experiment_artifacts(run)
        return run
    finally:
        if not request.persist_experiment_skills_to_main_library:
            write_json("skills.json", skill_snapshot)
