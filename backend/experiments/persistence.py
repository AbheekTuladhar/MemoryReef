from __future__ import annotations

import csv

from backend.models import ExperimentRun
from backend.tools.json_store import DATA_DIR, read_json, write_json


CSV_FIELDS = [
    "run_id",
    "pair_id",
    "condition_id",
    "matched_expected",
    "confidence",
    "likely_cause",
    "skills_used",
    "evidence_count",
    "trace_id",
    "reflection_id",
    "verification_status",
]


def save_experiment_json(run: ExperimentRun) -> None:
    runs = read_json("experiment_runs.json", [])
    runs.append(run.model_dump())
    write_json("experiment_runs.json", runs)


def save_experiment_csv(run: ExperimentRun) -> None:
    path = DATA_DIR / "experiment_results.csv"
    rows = []
    for scenario_result in run.scenario_results:
        for condition_result in scenario_result.condition_results:
            rows.append(
                {
                    "run_id": run.run_id,
                    "pair_id": scenario_result.pair_id,
                    "condition_id": condition_result.condition_id,
                    "matched_expected": condition_result.matched_expected,
                    "confidence": condition_result.answer.confidence,
                    "likely_cause": condition_result.answer.likely_cause,
                    "skills_used": ";".join(condition_result.skills_used),
                    "evidence_count": len(condition_result.answer.evidence),
                    "trace_id": condition_result.trace_id or "",
                    "reflection_id": condition_result.reflection_id or "",
                    "verification_status": condition_result.verification_status or "",
                }
            )
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def save_paper_summary(run: ExperimentRun) -> None:
    summary = run.metric_summary
    condition_names = ", ".join(summary.conditions_run)
    lines = [
        "# LogLearner Experiment Summary",
        "",
        f"Run ID: `{run.run_id}`",
        f"Created at: `{run.created_at}`",
        "",
        "## Hypothesis",
        "",
        run.hypothesis,
        "",
        "## Method",
        "",
        "Each configured scenario pair was run through baseline, learning, reuse, and any requested control conditions. "
        "Skills were snapshotted and restored unless persistence to the main skill library was requested.",
        "",
        "## Dataset",
        "",
        f"- Scenario pairs: {summary.total_pairs}",
        f"- Deterministic mode: {run.reproducibility.get('deterministic_mode', True)}",
        f"- Dataset source: {run.reproducibility.get('dataset', 'backend/data/scenarios.json')}",
        "",
        "## Experimental Conditions",
        "",
        f"Conditions run: {condition_names}",
        "",
        "- Baseline: test scenario with no saved skills.",
        "- Learning: paired learn scenario followed by reflection and optional verification.",
        "- Reuse: paired test scenario with learned skill retrieval enabled.",
        "- Random skill: paired test scenario with an unrelated skill control, when enabled.",
        "",
        "## Metrics",
        "",
        "- Accuracy: fraction of condition answers matching the expected answer.",
        "- Matched expected: raw count of correct condition answers.",
        "- Confidence: mean reported Investigator confidence.",
        "- Confidence delta: reuse confidence minus baseline confidence for each pair.",
        "- Evidence quality proxy: average number of cited evidence items.",
        "- Skill retrieval success: fraction of reuse runs where at least one skill was applied.",
        "- Overconfident wrong answers: wrong answers above the configured confidence threshold.",
        "",
        "## Results",
        "",
        f"- Total pairs: {summary.total_pairs}",
        f"- Conditions run: {', '.join(summary.conditions_run)}",
        f"- Accuracy by condition: {summary.accuracy_by_condition}",
        f"- Matched expected by condition: {summary.matched_expected_by_condition}",
        f"- Average confidence by condition: {summary.average_confidence_by_condition}",
        f"- Confidence delta by pair: {summary.confidence_delta_by_pair}",
        f"- Evidence quality proxy by condition: {summary.evidence_quality_proxy_by_condition}",
        f"- Skill retrieval success rate: {summary.skill_retrieval_success_rate}",
        f"- Verifier approval rate: {summary.verifier_approval_rate}",
        f"- Improvement rate: {summary.improvement_rate}",
        f"- Overconfident wrong answers: {summary.overconfident_wrong_answers}",
        f"- Duplicate skill rejections: {summary.duplicate_skill_rejections}",
        "",
        "### Results Table",
        "",
        "| Pair | Condition | Matched | Confidence | Answer |",
        "| --- | --- | --- | --- | --- |",
    ]
    for scenario_result in run.scenario_results:
        for condition_result in scenario_result.condition_results:
            answer = condition_result.answer.likely_cause.replace("|", "/")
            lines.append(
                f"| {scenario_result.pair_id} | {condition_result.condition_id} | "
                f"{condition_result.matched_expected} | {condition_result.answer.confidence:.2f} | {answer} |"
            )
    lines.extend(
        [
            "",
            "## Qualitative Examples",
            "",
        ]
    )
    for scenario_result in run.scenario_results[:3]:
        baseline = next((item for item in scenario_result.condition_results if item.condition_id == "baseline"), None)
        reuse = next((item for item in scenario_result.condition_results if item.condition_id == "reuse"), None)
        if baseline and reuse:
            lines.append(f"### {scenario_result.pair_id}")
            lines.append("")
            lines.append(f"- Baseline answer: {baseline.answer.likely_cause}")
            lines.append(f"- Reuse answer: {reuse.answer.likely_cause}")
            lines.append(f"- Learned skill IDs: {', '.join(scenario_result.learned_skill_ids) or 'none'}")
            lines.append(f"- Improvement detected: {scenario_result.improvement_detected}")
            lines.append("")
    lines.extend(
        [
        "## Per-Pair Notes",
        "",
        ]
    )
    for scenario_result in run.scenario_results:
        lines.append(f"### {scenario_result.pair_id}")
        lines.append("")
        lines.append(f"- Learned skill IDs: {', '.join(scenario_result.learned_skill_ids) or 'none'}")
        lines.append(f"- Improvement detected: {scenario_result.improvement_detected}")
        for condition_result in scenario_result.condition_results:
            lines.append(
                f"- {condition_result.condition_id}: matched={condition_result.matched_expected}, "
                f"confidence={condition_result.answer.confidence}, answer={condition_result.answer.likely_cause}"
            )
        lines.append("")
    lines.extend(
        [
            "## Limitations",
            "",
            "This is a small curated prototype benchmark. Results are useful for feasibility analysis, "
            "but they are not statistically generalizable without a larger and more diverse scenario set.",
            "",
            "## Future Work",
            "",
            "- Add more held-out scenarios and human labels.",
            "- Compare against stronger baselines and unrelated-skill controls.",
            "- Add blinded human evaluation of evidence quality.",
            "- Measure behavior on user-uploaded projects without storing private source in public artifacts.",
        ]
    )
    (DATA_DIR / "paper_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def save_experiment_artifacts(run: ExperimentRun) -> None:
    save_experiment_json(run)
    save_experiment_csv(run)
    save_paper_summary(run)
