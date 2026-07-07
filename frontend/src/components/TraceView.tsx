import { Trace } from "../types";

export function TraceView({ trace }: { trace?: Trace }) {
  if (!trace) return null;
  return (
    <section className="panel">
      <h2>Trace</h2>
      <div className="traceList">
        {trace.steps.map((step) => (
          <div className="traceStep" key={`${trace.trace_id}-${step.step}`}>
            <span>{step.step}</span>
            <div>
              <strong>{step.action}</strong>
              <p>{step.observation}</p>
              <p className="subtle">{step.reasoning_summary}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
