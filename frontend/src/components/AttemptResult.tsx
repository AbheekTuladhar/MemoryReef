import { Trace } from "../types";

export function AttemptResult({ trace }: { trace?: Trace }) {
  if (!trace) {
    return (
      <section className="panel mutedPanel">
        <h2>Attempt Result</h2>
        <p>No attempt has run yet.</p>
      </section>
    );
  }
  return (
    <section className="panel">
      <h2>Attempt Result</h2>
      <div className="answerGrid">
        <div>
          <span className="label">Likely cause</span>
          <strong>{trace.final_answer.likely_cause}</strong>
        </div>
        <div>
          <span className="label">Confidence</span>
          <strong>{Math.round(trace.final_answer.confidence * 100)}%</strong>
        </div>
        <div>
          <span className="label">Matched expected</span>
          <strong>{trace.matched_expected ? "Yes" : "No"}</strong>
        </div>
      </div>
      <div className="usedSkillBox">
        <span className="label">Saved skills applied</span>
        <strong>{trace.used_skills.length ? trace.used_skills.join(", ") : "None"}</strong>
      </div>
      <h3>Evidence</h3>
      <ul>
        {trace.final_answer.evidence.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
      <h3>Next checks</h3>
      <ul>
        {trace.final_answer.next_checks.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}
