import { AgentLog } from "../types";

export function AgentLogPanel({ logs }: { logs: AgentLog[] }) {
  return (
    <section className="panel">
      <h2>Agent Activity Logs</h2>
      <p className="subtle">Summarized agent reasoning and decisions. Hidden chain-of-thought is not stored.</p>
      {logs.length === 0 ? (
        <p>No agent logs yet.</p>
      ) : (
        <div className="agentLogList">
          {logs.map((log, index) => (
            <article className="agentLog" key={`${log.agent}-${log.event}-${index}`}>
              <div className="agentLogHeader">
                <strong>{log.agent}</strong>
                <span>{Math.round(log.confidence * 100)}%</span>
              </div>
              <span className="label">{log.event}</span>
              <p>{log.summary}</p>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
