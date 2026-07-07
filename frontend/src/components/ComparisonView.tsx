import { ArrowRight, GitCompare, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Trace } from "../types";

type Comparison = {
  scenario_id: string;
  without_skill: Trace;
  with_skill: Trace;
  comparison: { improved: boolean; confidence_delta: number; summary: string; expected_answer: string; skills_used: string[] };
};

function pct(value: number) {
  return Math.round(value * 100);
}

export function ComparisonView({
  comparison,
  onCompare,
  running = false,
  disabled = false
}: {
  comparison?: Comparison;
  onCompare: () => void;
  running?: boolean;
  disabled?: boolean;
}) {
  // reveal drives the fill + flip animations; re-arm it whenever a fresh comparison lands (new object ref).
  const [reveal, setReveal] = useState(false);
  useEffect(() => {
    if (!comparison) return;
    setReveal(false);
    const timer = setTimeout(() => setReveal(true), 80);
    return () => clearTimeout(timer);
  }, [comparison]);

  const before = comparison?.without_skill.final_answer;
  const after = comparison?.with_skill.final_answer;
  const beforeRight = comparison?.without_skill.matched_expected ?? false;
  const afterRight = comparison?.with_skill.matched_expected ?? false;

  return (
    <section className="panel revealPanel">
      <div className="panelHeader">
        <div>
          <span className="eyebrow">The reveal</span>
          <h2>Before / After</h2>
          <p>Run the paired test cold, then again with the reef's memory.</p>
        </div>
        <button
          className="primaryButton"
          onClick={onCompare}
          disabled={running || disabled}
          title="Compare paired scenario"
        >
          {running ? <Loader2 size={16} className="spin" /> : <GitCompare size={16} />}
          {running ? "Replaying…" : "Compare"}
        </button>
      </div>

      {!comparison || !before || !after ? (
        <p className="subtle">No comparison yet. Save a skill, then compare the paired test to see the difference.</p>
      ) : (
        <>
          <div className="revealGrid">
            <article className={`revealCard cold${reveal ? " show" : ""}`}>
              <header>
                <span className="revealTag">Without the reef</span>
                <span className={`verdict ${beforeRight ? "right" : "wrong"}`}>{beforeRight ? "✓" : "✕"}</span>
              </header>
              <strong className="revealCause">{before.likely_cause}</strong>
              <div className="confTrack">
                <i style={{ width: reveal ? `${pct(before.confidence)}%` : "0%" }} />
              </div>
              <span className="confValue">{pct(before.confidence)}% confidence</span>
            </article>

            <div className={`revealFlip${reveal ? " show" : ""}`} aria-hidden="true">
              <ArrowRight size={26} />
            </div>

            <article className={`revealCard warm${reveal ? " show" : ""}`}>
              <header>
                <span className="revealTag">With the reef</span>
                <span className={`verdict ${afterRight ? "right" : "wrong"}`}>{afterRight ? "✓" : "✕"}</span>
              </header>
              <strong className="revealCause">{after.likely_cause}</strong>
              <div className="confTrack">
                <i className="warm" style={{ width: reveal ? `${pct(after.confidence)}%` : "0%" }} />
              </div>
              <span className="confValue">{pct(after.confidence)}% confidence</span>
            </article>
          </div>

          <p className={`revealVerdict ${comparison.comparison.improved ? "up" : "flat"}`}>{comparison.comparison.summary}</p>
          <p className="revealMeta">
            Expected: {comparison.comparison.expected_answer}
            <span className="revealSkills">Skills used: {comparison.comparison.skills_used.join(", ") || "none"}</span>
          </p>
        </>
      )}
    </section>
  );
}
