export type Scenario = {
  scenario_id: string;
  title: string;
  pair_id: string;
  purpose: "learn" | "test" | "custom";
  task: string;
  input_text: string;
  expected_answer: string;
  common_mistake: string;
  target_skill: string;
  paired_scenario_id?: string;
};

export type Skill = {
  skill_id: string;
  name: string;
  description: string;
  when_to_use: string[];
  steps: string[];
  anti_pattern: string;
  source_trace_id?: string;
  tags: string[];
  usage_count: number;
  status: string;
};

export type AgentLog = {
  agent: string;
  event: string;
  summary: string;
  confidence: number;
};

export type Trace = {
  trace_id: string;
  scenario_id: string;
  used_skills: string[];
  steps: Array<{ step: number; action: string; observation: string; reasoning_summary: string }>;
  agent_logs: AgentLog[];
  final_answer: {
    likely_cause: string;
    confidence: number;
    evidence: string[];
    next_checks: string[];
  };
  matched_expected: boolean;
};

export type ReflectionPayload = {
  what_happened: string;
  lesson: string;
  confidence: number;
  agent_logs: AgentLog[];
};

export type VerificationPayload = {
  status: string;
  reason: string;
  confidence: number;
  agent_logs: AgentLog[];
  final_skill?: Skill;
};

export type ExperimentRequestPayload = {
  conditions?: string[];
  verifier_enabled: boolean;
  reflection_enabled: boolean;
  skill_retrieval_enabled: boolean;
  duplicate_filtering_enabled: boolean;
  random_skill_control_enabled: boolean;
  persist_experiment_skills_to_main_library: boolean;
};

export type ExperimentConditionResult = {
  condition_id: string;
  answer: Trace["final_answer"];
  matched_expected: boolean;
  skills_used: string[];
  trace_id?: string;
  reflection_id?: string;
  verification_status?: string;
  agent_logs: AgentLog[];
};

export type ExperimentScenarioResult = {
  pair_id: string;
  learn_scenario_id: string;
  test_scenario_id: string;
  target_skill: string;
  condition_results: ExperimentConditionResult[];
  learned_skill_ids: string[];
  improvement_detected: boolean;
  notes: string[];
};

export type ExperimentMetricSummary = {
  total_pairs: number;
  conditions_run: string[];
  accuracy_by_condition: Record<string, number>;
  matched_expected_by_condition: Record<string, number>;
  average_confidence_by_condition: Record<string, number>;
  confidence_delta_by_pair: Record<string, number>;
  evidence_quality_proxy_by_condition: Record<string, number>;
  improvement_rate: number;
  skill_retrieval_success_rate: number;
  verifier_approval_rate: number;
  duplicate_skill_rejections: number;
  overconfident_wrong_answers: number;
};

export type ExperimentRun = {
  run_id: string;
  config_id: string;
  hypothesis: string;
  created_at: string;
  request: ExperimentRequestPayload;
  scenario_results: ExperimentScenarioResult[];
  metric_summary: ExperimentMetricSummary;
  ablation_flags: Record<string, boolean>;
  reproducibility: Record<string, unknown>;
};

export type ExperimentConfig = {
  experiment_id: string;
  title: string;
  hypothesis: string;
  conditions: Array<{ condition_id: string; name: string; description: string }>;
  scenario_pairs: Array<{ pair_id: string; name: string; learn_scenario_id: string; test_scenario_id: string }>;
};
