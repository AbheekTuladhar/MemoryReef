import { GitCompare } from "lucide-react";
import { Trace } from "../types";

type Comparison = {
  scenario_id: string;
  without_skill: Trace;
  with_skill: Trace;
  comparison: { improved: boolean; confidence_delta: number; summary: string; expected_answer: string; skills_used: string[] };
};

export function ComparisonView({ comparison, onCompare }: { comparison?: Comparison; onCompare: () => void }) {
  return (
    <section className="panel">
      <div className="panelHeader">
        <div>
          <h2>Before / After</h2>
          <p>Run the paired test without and with saved skills.</p>
        </div>
        <button className="secondaryButton" onClick={onCompare} title="Compare paired scenario">
          <GitCompare size={16} />
          Compare
        </button>
      </div>
      {!comparison ? (
        <p>No comparison has run yet.</p>
      ) : (
        <>
          <div className="compareGrid">
            <div>
              <span className="label">Without skill</span>
              <strong>{comparison.without_skill.final_answer.likely_cause}</strong>
              <p>{Math.round(comparison.without_skill.final_answer.confidence * 100)}% confidence</p>
            </div>
            <div>
              <span className="label">With skill</span>
              <strong>{comparison.with_skill.final_answer.likely_cause}</strong>
              <p>{Math.round(comparison.with_skill.final_answer.confidence * 100)}% confidence</p>
            </div>
          </div>
          <p className={comparison.comparison.improved ? "successText" : "warnText"}>{comparison.comparison.summary}</p>
          <p>Skills used: {comparison.comparison.skills_used.join(", ") || "none"}</p>
        </>
      )}
    </section>
  );
}
