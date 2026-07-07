# LogLearner Experiment Summary

Run ID: `experiment_18e5671735`
Created at: `2026-07-03T22:12:21.708137+00:00`

## Hypothesis

Agents that reflect on their own debugging traces and store verified reusable skills will solve related debugging tasks more accurately than agents without saved skills.

## Method

Each configured scenario pair was run through baseline, learning, reuse, and any requested control conditions. Skills were snapshotted and restored unless persistence to the main skill library was requested.

## Dataset

- Scenario pairs: 4
- Deterministic mode: True
- Dataset source: backend/data/scenarios.json

## Experimental Conditions

Conditions run: baseline, learning, random_skill, reuse

- Baseline: test scenario with no saved skills.
- Learning: paired learn scenario followed by reflection and optional verification.
- Reuse: paired test scenario with learned skill retrieval enabled.
- Random skill: paired test scenario with an unrelated skill control, when enabled.

## Metrics

- Accuracy: fraction of condition answers matching the expected answer.
- Matched expected: raw count of correct condition answers.
- Confidence: mean reported Investigator confidence.
- Confidence delta: reuse confidence minus baseline confidence for each pair.
- Evidence quality proxy: average number of cited evidence items.
- Skill retrieval success: fraction of reuse runs where at least one skill was applied.
- Overconfident wrong answers: wrong answers above the configured confidence threshold.

## Results

- Total pairs: 4
- Conditions run: baseline, learning, random_skill, reuse
- Accuracy by condition: {'baseline': 0.0, 'learning': 1.0, 'random_skill': 0.0, 'reuse': 1.0}
- Matched expected by condition: {'baseline': 0, 'learning': 4, 'random_skill': 0, 'reuse': 4}
- Average confidence by condition: {'baseline': 0.562, 'learning': 0.745, 'random_skill': 0.562, 'reuse': 0.8}
- Confidence delta by pair: {'loudest_error': 0.26, 'deployment_suspicion': 0.31, 'retry_storm': 0.25, 'missing_evidence': 0.13}
- Evidence quality proxy by condition: {'baseline': 1.0, 'learning': 1.75, 'random_skill': 1.0, 'reuse': 2.0}
- Skill retrieval success rate: 1.0
- Verifier approval rate: 1.0
- Improvement rate: 1.0
- Overconfident wrong answers: 0
- Duplicate skill rejections: 0

### Results Table

| Pair | Condition | Matched | Confidence | Answer |
| --- | --- | --- | --- | --- |
| loudest_error | baseline | False | 0.58 | Frontend service issue |
| loudest_error | learning | True | 0.78 | Database connection exhaustion |
| loudest_error | reuse | True | 0.84 | Redis memory exhaustion |
| loudest_error | random_skill | False | 0.58 | Frontend service issue |
| deployment_suspicion | baseline | False | 0.55 | Gateway issue |
| deployment_suspicion | learning | True | 0.78 | Missing JWT_SECRET environment variable after deployment |
| deployment_suspicion | reuse | True | 0.86 | Unknown CHECKOUT_V2 feature flag after deployment |
| deployment_suspicion | random_skill | False | 0.55 | Gateway issue |
| retry_storm | baseline | False | 0.57 | API rate limiting |
| retry_storm | learning | True | 0.78 | Inventory timeout caused retry amplification and queue growth |
| retry_storm | reuse | True | 0.82 | Email service slowdown caused retry amplification and backlog growth |
| retry_storm | random_skill | False | 0.57 | API rate limiting |
| missing_evidence | baseline | False | 0.55 | Gateway issue |
| missing_evidence | learning | True | 0.64 | Insufficient evidence; ask for deployment logs, dependency logs, and fuller timing |
| missing_evidence | reuse | True | 0.68 | Insufficient evidence; ask for auth-service logs, deployment events, or secret rotation history |
| missing_evidence | random_skill | False | 0.55 | Gateway issue |

## Qualitative Examples

### loudest_error

- Baseline answer: Frontend service issue
- Reuse answer: Redis memory exhaustion
- Learned skill IDs: skill_avoid_the_loudest_error_trap_dcf048
- Improvement detected: True

### deployment_suspicion

- Baseline answer: Gateway issue
- Reuse answer: Unknown CHECKOUT_V2 feature flag after deployment
- Learned skill IDs: skill_check_recent_deployment_configuration_a62f7b
- Improvement detected: True

### retry_storm

- Baseline answer: API rate limiting
- Reuse answer: Email service slowdown caused retry amplification and backlog growth
- Learned skill IDs: skill_detect_retry_amplification_9dbade
- Improvement detected: True

## Per-Pair Notes

### loudest_error

- Learned skill IDs: skill_avoid_the_loudest_error_trap_dcf048
- Improvement detected: True
- baseline: matched=False, confidence=0.58, answer=Frontend service issue
- learning: matched=True, confidence=0.78, answer=Database connection exhaustion
- reuse: matched=True, confidence=0.84, answer=Redis memory exhaustion
- random_skill: matched=False, confidence=0.58, answer=Frontend service issue

### deployment_suspicion

- Learned skill IDs: skill_check_recent_deployment_configuration_a62f7b
- Improvement detected: True
- baseline: matched=False, confidence=0.55, answer=Gateway issue
- learning: matched=True, confidence=0.78, answer=Missing JWT_SECRET environment variable after deployment
- reuse: matched=True, confidence=0.86, answer=Unknown CHECKOUT_V2 feature flag after deployment
- random_skill: matched=False, confidence=0.55, answer=Gateway issue

### retry_storm

- Learned skill IDs: skill_detect_retry_amplification_9dbade
- Improvement detected: True
- baseline: matched=False, confidence=0.57, answer=API rate limiting
- learning: matched=True, confidence=0.78, answer=Inventory timeout caused retry amplification and queue growth
- reuse: matched=True, confidence=0.82, answer=Email service slowdown caused retry amplification and backlog growth
- random_skill: matched=False, confidence=0.57, answer=API rate limiting

### missing_evidence

- Learned skill IDs: skill_ask_for_missing_evidence_before_guessing_3975c3
- Improvement detected: True
- baseline: matched=False, confidence=0.55, answer=Gateway issue
- learning: matched=True, confidence=0.64, answer=Insufficient evidence; ask for deployment logs, dependency logs, and fuller timing
- reuse: matched=True, confidence=0.68, answer=Insufficient evidence; ask for auth-service logs, deployment events, or secret rotation history
- random_skill: matched=False, confidence=0.55, answer=Gateway issue

## Limitations

This is a small curated prototype benchmark. Results are useful for feasibility analysis, but they are not statistically generalizable without a larger and more diverse scenario set.

## Future Work

- Add more held-out scenarios and human labels.
- Compare against stronger baselines and unrelated-skill controls.
- Add blinded human evaluation of evidence quality.
- Measure behavior on user-uploaded projects without storing private source in public artifacts.
