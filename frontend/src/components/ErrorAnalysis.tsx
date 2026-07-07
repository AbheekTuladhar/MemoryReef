import { ExperimentRun } from "../types";

export function ErrorAnalysis({ run }: { run?: ExperimentRun }) {
  if (!run) {
    return (
      <section className="panel">
        <h2>Error Analysis</h2>
        <p>No experiment run yet.</p>
      </section>
    );
  }

  const improvements = run.scenario_results.filter((result) => result.improvement_detected);
  const noChange = run.scenario_results.filter((result) => !result.improvement_detected);
  const wrongAnswers = run.scenario_results.flatMap((scenario) =>
    scenario.condition_results
      .filter((condition) => !condition.matched_expected)
      .map((condition) => ({ scenario, condition }))
  );
  const overconfidentWrong = wrongAnswers.filter(({ condition }) => condition.answer.confidence >= 0.75);
  const rejectedOrDuplicate = run.scenario_results.filter((scenario) =>
    scenario.notes.some((note) => note.toLowerCase().includes("duplicate")) ||
    scenario.condition_results.some((condition) => condition.verification_status === "rejected")
  );
  const retrievalMismatches = run.scenario_results.filter((scenario) => {
    const reuse = scenario.condition_results.find((condition) => condition.condition_id === "reuse");
    return reuse && reuse.skills_used.length === 0;
  });

  return (
    <section className="panel">
      <h2>Error Analysis</h2>
      <div className="metricGrid">
        <div><span className="label">Improvements</span><strong>{improvements.length}</strong></div>
        <div><span className="label">No-change cases</span><strong>{noChange.length}</strong></div>
        <div><span className="label">Wrong answers</span><strong>{wrongAnswers.length}</strong></div>
        <div><span className="label">Overconfident wrong</span><strong>{overconfidentWrong.length}</strong></div>
      </div>
      <h3>Wrong Answers</h3>
      {wrongAnswers.length === 0 ? <p>None.</p> : (
        <ul>
          {wrongAnswers.map(({ scenario, condition }) => (
            <li key={`${scenario.pair_id}-${condition.condition_id}`}>
              {scenario.pair_id} / {condition.condition_id}: {condition.answer.likely_cause} ({Math.round(condition.answer.confidence * 100)}%)
            </li>
          ))}
        </ul>
      )}
      <h3>Rejected Or Duplicate Skills</h3>
      {rejectedOrDuplicate.length === 0 ? <p>None detected.</p> : (
        <ul>{rejectedOrDuplicate.map((scenario) => <li key={scenario.pair_id}>{scenario.pair_id}: {scenario.notes.join("; ") || "Puffer rejected a skill."}</li>)}</ul>
      )}
      <h3>Retrieved Skill Mismatches</h3>
      {retrievalMismatches.length === 0 ? <p>None detected.</p> : (
        <ul>{retrievalMismatches.map((scenario) => <li key={scenario.pair_id}>{scenario.pair_id}: reuse ran without retrieved skills.</li>)}</ul>
      )}
    </section>
  );
}
