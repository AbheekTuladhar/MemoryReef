import {
  AgentLog,
  ExperimentConfig,
  ExperimentRequestPayload,
  ExperimentRun,
  ReflectionPayload,
  Scenario,
  Skill,
  Trace,
  VerificationPayload
} from "./types";

export const API_BASE = "http://127.0.0.1:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

export const api = {
  scenarios: () => request<{ scenarios: Scenario[] }>("/api/scenarios"),
  skills: () => request<{ skills: Skill[] }>("/api/skills"),
  experimentConfig: () => request<ExperimentConfig>("/api/experiments/config"),
  latestExperiment: () => request<{ run: ExperimentRun }>("/api/experiments/latest"),
  runExperiment: (payload: ExperimentRequestPayload) =>
    request<{ run: ExperimentRun }>("/api/experiments/run", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  createCustomScenario: (payload: {
    title: string;
    task: string;
    input_text: string;
    expected_answer?: string;
    target_skill?: string;
    project_zip_base64?: string;
    project_zip_filename?: string;
  }) =>
    request<{ scenario: Scenario; project_summary: { summary: string; files: string[] } }>("/api/custom-scenarios", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  attempt: (scenario_id: string, use_skills: boolean) =>
    request<{ trace: Trace; answer: Trace["final_answer"]; skills_used: Skill[]; agent_logs: AgentLog[] }>("/api/attempt", {
      method: "POST",
      body: JSON.stringify({ scenario_id, use_skills })
    }),
  reflect: (trace_id: string) =>
    request<{ reflection: ReflectionPayload; proposed_skill: Skill; agent_logs: AgentLog[] }>("/api/reflect", {
      method: "POST",
      body: JSON.stringify({ trace_id })
    }),
  verifySkill: (skill: Skill) =>
    request<VerificationPayload>("/api/verify-skill", {
      method: "POST",
      body: JSON.stringify({ skill })
    }),
  saveSkill: (skill: Skill) =>
    request<{ skill: Skill }>("/api/save-skill", {
      method: "POST",
      body: JSON.stringify({ skill })
    }),
  compare: (scenario_id: string) =>
    request<{
      scenario_id: string;
      without_skill: Trace;
      with_skill: Trace;
      agent_logs: AgentLog[];
      comparison: { improved: boolean; confidence_delta: number; summary: string; expected_answer: string; skills_used: string[] };
    }>("/api/compare", {
      method: "POST",
      body: JSON.stringify({ scenario_id })
    })
};
