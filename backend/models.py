from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Scenario(BaseModel):
    scenario_id: str
    title: str
    pair_id: str
    purpose: Literal["learn", "test", "custom"]
    task: str
    input_text: str
    expected_answer: str
    common_mistake: str
    target_skill: str
    paired_scenario_id: str | None = None


class TraceStep(BaseModel):
    step: int
    action: str
    observation: str
    reasoning_summary: str


class AgentLog(BaseModel):
    agent: str
    event: str
    summary: str
    confidence: float


class FinalAnswer(BaseModel):
    likely_cause: str
    confidence: float
    evidence: list[str]
    next_checks: list[str] = Field(default_factory=list)


class AttemptTrace(BaseModel):
    trace_id: str
    scenario_id: str
    used_skills: list[str]
    steps: list[TraceStep]
    agent_logs: list[AgentLog] = Field(default_factory=list)
    final_answer: FinalAnswer
    matched_expected: bool


class Skill(BaseModel):
    skill_id: str
    name: str
    description: str
    when_to_use: list[str]
    steps: list[str]
    anti_pattern: str
    source_trace_id: str | None = None
    tags: list[str]
    usage_count: int = 0
    status: Literal["proposed", "approved", "rejected", "revised"] = "proposed"


class Reflection(BaseModel):
    reflection_id: str
    trace_id: str
    what_happened: str
    lesson: str
    proposed_skill_id: str
    confidence: float = 0.74
    agent_logs: list[AgentLog] = Field(default_factory=list)


class Verification(BaseModel):
    status: Literal["approved", "revised", "rejected"]
    reason: str
    final_skill: Skill | None = None
    confidence: float = 0.78
    agent_logs: list[AgentLog] = Field(default_factory=list)


class AttemptRequest(BaseModel):
    scenario_id: str
    use_skills: bool = False


class TraceRequest(BaseModel):
    trace_id: str


class SkillRequest(BaseModel):
    skill: Skill


class CompareRequest(BaseModel):
    scenario_id: str


class ExperimentRequest(BaseModel):
    config_id: str = "loglearner_small_data_learning_v1"
    scenario_pair_ids: list[str] | None = None
    conditions: list[str] | None = None
    verifier_enabled: bool = True
    reflection_enabled: bool = True
    skill_retrieval_enabled: bool = True
    duplicate_filtering_enabled: bool = True
    random_skill_control_enabled: bool = True
    persist_experiment_skills_to_main_library: bool = False


class CustomScenarioRequest(BaseModel):
    title: str = "Custom Logs"
    task: str = "Find the likely cause or next debugging step from these logs."
    input_text: str
    expected_answer: str = "User-provided scenario; no expected answer supplied"
    target_skill: str = "Custom Debugging Lesson"
    project_zip_base64: str | None = None
    project_zip_filename: str | None = None


class ExperimentConditionResult(BaseModel):
    condition_id: str
    answer: FinalAnswer
    matched_expected: bool
    skills_used: list[str] = Field(default_factory=list)
    trace_id: str | None = None
    reflection_id: str | None = None
    verification_status: str | None = None
    agent_logs: list[AgentLog] = Field(default_factory=list)


class ExperimentScenarioResult(BaseModel):
    pair_id: str
    learn_scenario_id: str
    test_scenario_id: str
    target_skill: str
    condition_results: list[ExperimentConditionResult]
    learned_skill_ids: list[str] = Field(default_factory=list)
    improvement_detected: bool = False
    notes: list[str] = Field(default_factory=list)


class ExperimentMetricSummary(BaseModel):
    total_pairs: int
    conditions_run: list[str]
    accuracy_by_condition: dict[str, float]
    matched_expected_by_condition: dict[str, int] = Field(default_factory=dict)
    average_confidence_by_condition: dict[str, float]
    confidence_delta_by_pair: dict[str, float] = Field(default_factory=dict)
    evidence_quality_proxy_by_condition: dict[str, float] = Field(default_factory=dict)
    improvement_rate: float
    skill_retrieval_success_rate: float
    verifier_approval_rate: float
    duplicate_skill_rejections: int
    overconfident_wrong_answers: int


class ExperimentRun(BaseModel):
    run_id: str
    config_id: str
    hypothesis: str
    created_at: str
    request: ExperimentRequest
    scenario_results: list[ExperimentScenarioResult]
    metric_summary: ExperimentMetricSummary
    ablation_flags: dict[str, bool]
    reproducibility: dict[str, Any] = Field(default_factory=dict)


class CompareResult(BaseModel):
    scenario_id: str
    without_skill: dict[str, Any]
    with_skill: dict[str, Any]
    comparison: dict[str, Any]
