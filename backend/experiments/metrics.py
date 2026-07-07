from __future__ import annotations

from collections import defaultdict

from backend.models import ExperimentMetricSummary, ExperimentScenarioResult


def calculate_metric_summary(results: list[ExperimentScenarioResult], config: dict) -> ExperimentMetricSummary:
    correct: dict[str, int] = defaultdict(int)
    totals: dict[str, int] = defaultdict(int)
    confidence: dict[str, float] = defaultdict(float)
    evidence_counts: dict[str, int] = defaultdict(int)
    confidence_delta_by_pair: dict[str, float] = {}

    skill_reuse_hits = 0
    reuse_total = 0
    verifier_saveable = 0
    verifier_total = 0
    duplicate_rejections = 0
    overconfident_wrong = 0
    improvements = 0
    threshold = config.get("metric_thresholds", {}).get("overconfidence_confidence_threshold", 0.75)

    for scenario_result in results:
        by_condition = {result.condition_id: result for result in scenario_result.condition_results}
        baseline = by_condition.get("baseline")
        reuse = by_condition.get("reuse")
        if baseline and reuse:
            confidence_delta_by_pair[scenario_result.pair_id] = round(
                reuse.answer.confidence - baseline.answer.confidence,
                3,
            )
        if scenario_result.improvement_detected:
            improvements += 1
        for note in scenario_result.notes:
            if "duplicate" in note:
                duplicate_rejections += 1
        for result in scenario_result.condition_results:
            totals[result.condition_id] += 1
            correct[result.condition_id] += int(result.matched_expected)
            confidence[result.condition_id] += result.answer.confidence
            evidence_counts[result.condition_id] += len(result.answer.evidence)
            if result.condition_id == "reuse":
                reuse_total += 1
                skill_reuse_hits += int(bool(result.skills_used))
            if result.condition_id == "learning" and result.verification_status:
                verifier_total += 1
                verifier_saveable += int(result.verification_status in {"approved", "revised", "skipped"})
            if not result.matched_expected and result.answer.confidence >= threshold:
                overconfident_wrong += 1

    conditions_run = sorted(totals)
    accuracy = {condition: round(correct[condition] / totals[condition], 3) for condition in conditions_run if totals[condition]}
    avg_confidence = {
        condition: round(confidence[condition] / totals[condition], 3) for condition in conditions_run if totals[condition]
    }
    evidence_proxy = {
        condition: round(evidence_counts[condition] / totals[condition], 3)
        for condition in conditions_run
        if totals[condition]
    }

    return ExperimentMetricSummary(
        total_pairs=len(results),
        conditions_run=conditions_run,
        accuracy_by_condition=accuracy,
        matched_expected_by_condition={condition: correct[condition] for condition in conditions_run},
        average_confidence_by_condition=avg_confidence,
        confidence_delta_by_pair=confidence_delta_by_pair,
        evidence_quality_proxy_by_condition=evidence_proxy,
        improvement_rate=round(improvements / len(results), 3) if results else 0.0,
        skill_retrieval_success_rate=round(skill_reuse_hits / reuse_total, 3) if reuse_total else 0.0,
        verifier_approval_rate=round(verifier_saveable / verifier_total, 3) if verifier_total else 0.0,
        duplicate_skill_rejections=duplicate_rejections,
        overconfident_wrong_answers=overconfident_wrong,
    )
