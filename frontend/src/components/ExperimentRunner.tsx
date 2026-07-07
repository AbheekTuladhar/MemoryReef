import { Download, FlaskConical, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { api, API_BASE } from "../api";
import { ExperimentConfig, ExperimentRun } from "../types";
import { ErrorAnalysis } from "./ErrorAnalysis";

type ToggleKey =
  | "verifier_enabled"
  | "reflection_enabled"
  | "skill_retrieval_enabled"
  | "duplicate_filtering_enabled"
  | "random_skill_control_enabled"
  | "persist_experiment_skills_to_main_library";

const DEFAULT_CONDITIONS = ["baseline", "learning", "reuse", "random_skill"];

export function ExperimentRunner() {
  const [config, setConfig] = useState<ExperimentConfig | undefined>();
  const [run, setRun] = useState<ExperimentRun | undefined>();
  const [conditions, setConditions] = useState<string[]>(DEFAULT_CONDITIONS);
  const [flags, setFlags] = useState<Record<ToggleKey, boolean>>({
    verifier_enabled: true,
    reflection_enabled: true,
    skill_retrieval_enabled: true,
    duplicate_filtering_enabled: true,
    random_skill_control_enabled: true,
    persist_experiment_skills_to_main_library: false
  });
  const [status, setStatus] = useState("Research mode ready");

  useEffect(() => {
    api.experimentConfig().then(setConfig);
    api.latestExperiment().then((response) => setRun(response.run)).catch(() => undefined);
  }, []);

  function toggleCondition(conditionId: string) {
    setConditions((current) =>
      current.includes(conditionId) ? current.filter((item) => item !== conditionId) : [...current, conditionId]
    );
  }

  function toggleFlag(key: ToggleKey) {
    setFlags((current) => ({ ...current, [key]: !current[key] }));
  }

  async function runExperiment() {
    setStatus("Running experiment");
    const response = await api.runExperiment({ conditions, ...flags });
    setRun(response.run);
    setStatus("Experiment complete");
  }

  return (
    <>
      <section className="panel researchPanel">
        <div className="panelHeader">
          <div>
            <span className="eyebrow">Research Mode</span>
            <h2>Experiment Runner</h2>
            <p>{status}</p>
          </div>
          <button className="primaryButton" onClick={runExperiment} title="Run experiment">
            <FlaskConical size={16} />
            Run Experiment
          </button>
        </div>

        <div className="hypothesisBox">
          <span className="label">Hypothesis</span>
          <p>{config?.hypothesis ?? run?.hypothesis ?? "Loading experiment configuration..."}</p>
        </div>

        <h3>Conditions</h3>
        <div className="toggleGrid">
          {(config?.conditions ?? []).map((condition) => (
            <label className="checkCard" key={condition.condition_id}>
              <input
                type="checkbox"
                checked={conditions.includes(condition.condition_id)}
                onChange={() => toggleCondition(condition.condition_id)}
              />
              <span>{condition.name}</span>
            </label>
          ))}
        </div>

        <h3>Ablation Flags</h3>
        <div className="toggleGrid">
          {Object.entries(flags).map(([key, value]) => (
            <label className="checkCard" key={key}>
              <input type="checkbox" checked={value} onChange={() => toggleFlag(key as ToggleKey)} />
              <span>{key.replace(/_/g, " ")}</span>
            </label>
          ))}
        </div>

        {run && (
          <>
            <div className="metricGrid">
              <div><span className="label">Pairs</span><strong>{run.metric_summary.total_pairs}</strong></div>
              <div><span className="label">Improvement</span><strong>{Math.round(run.metric_summary.improvement_rate * 100)}%</strong></div>
              <div><span className="label">Skill retrieval</span><strong>{Math.round(run.metric_summary.skill_retrieval_success_rate * 100)}%</strong></div>
              <div><span className="label">Verifier approval</span><strong>{Math.round(run.metric_summary.verifier_approval_rate * 100)}%</strong></div>
            </div>
            <div className="buttonRow">
              <a className="downloadButton" href={`${API_BASE}/api/experiments/export/csv`}>
                <Download size={16} />
                CSV
              </a>
              <a className="downloadButton" href={`${API_BASE}/api/experiments/export/summary`}>
                <Download size={16} />
                Paper Summary
              </a>
              <button className="secondaryButton" onClick={() => api.latestExperiment().then((response) => setRun(response.run))}>
                <RefreshCw size={16} />
                Latest
              </button>
            </div>

            <div className="tableWrap">
              <table>
                <thead>
                  <tr>
                    <th>Pair</th>
                    <th>Condition</th>
                    <th>Matched</th>
                    <th>Confidence</th>
                    <th>Answer</th>
                  </tr>
                </thead>
                <tbody>
                  {run.scenario_results.flatMap((scenario) =>
                    scenario.condition_results.map((condition) => (
                      <tr key={`${scenario.pair_id}-${condition.condition_id}`}>
                        <td>{scenario.pair_id}</td>
                        <td>{condition.condition_id}</td>
                        <td>{condition.matched_expected ? "Yes" : "No"}</td>
                        <td>{Math.round(condition.answer.confidence * 100)}%</td>
                        <td>{condition.answer.likely_cause}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>
      <ErrorAnalysis run={run} />
    </>
  );
}
