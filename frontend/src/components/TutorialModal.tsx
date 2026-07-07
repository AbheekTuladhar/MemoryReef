import { BookOpen, Brain, GitCompare, Save, X } from "lucide-react";

type Props = {
  open: boolean;
  onClose: () => void;
};

const steps = [
  {
    icon: BookOpen,
    title: "1. Pick a tiny incident",
    body: "Choose a curated scenario, paste your own logs, or upload a text file. The logs are the teaching material for the learning loop."
  },
  {
    icon: Brain,
    title: "2. Run Dory",
    body: "Dory checks patterns and timing before giving a concise answer."
  },
  {
    icon: Save,
    title: "3. Let Nemo teach",
    body: "Nemo reviews Dory's trace and proposes one reusable debugging skill. Puffer checks it before saving."
  },
  {
    icon: GitCompare,
    title: "4. Reuse and compare",
    body: "Saved skills are retrieved for related scenarios. Usage counts increase when Dory actually applies a saved skill."
  }
];

export function TutorialModal({ open, onClose }: Props) {
  if (!open) return null;

  return (
    <div className="modalBackdrop" role="presentation">
      <section className="tutorialModal" role="dialog" aria-modal="true" aria-labelledby="tutorial-title">
        <div className="modalHeader">
          <div>
            <span className="eyebrow">Quick tour</span>
            <h2 id="tutorial-title">How MemoryReef learns</h2>
          </div>
          <button className="iconButton" onClick={onClose} title="Close tutorial" aria-label="Close tutorial">
            <X size={18} />
          </button>
        </div>

        <div className="animatedLoop" aria-hidden="true">
          <span>Dory attempts</span>
          <span>Nemo reflects</span>
          <span>Puffer approves</span>
          <span>Skill reused</span>
        </div>

        <div className="tutorialBody">
          {steps.map((step) => {
            const Icon = step.icon;
            return (
              <article className="tutorialStep" key={step.title}>
                <div className="tutorialIcon">
                  <Icon size={20} />
                </div>
                <div>
                  <h3>{step.title}</h3>
                  <p>{step.body}</p>
                </div>
              </article>
            );
          })}
          <div className="demoRecipe">
            <h3>Fast demo path</h3>
            <ol>
              <li>Run a learning scenario such as Database Connection Exhaustion, or add your own logs.</li>
              <li>Reflect, verify, and save the proposed skill.</li>
              <li>Click Compare to run the paired test before and after learning.</li>
              <li>Use Run with saved skills on any related task to see Dory apply Nemo's lesson.</li>
            </ol>
          </div>
        </div>
      </section>
    </div>
  );
}
