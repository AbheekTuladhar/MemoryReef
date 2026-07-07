import { Play } from "lucide-react";
import { CustomLogInput } from "./CustomLogInput";
import { Scenario } from "../types";

type Props = {
  scenarios: Scenario[];
  selectedId: string;
  onSelect: (id: string) => void;
  onRun: () => void;
  customTitle: string;
  customTask: string;
  customInput: string;
  customExpected: string;
  customSkill: string;
  projectZipName: string;
  onCustomTitleChange: (value: string) => void;
  onCustomTaskChange: (value: string) => void;
  onCustomInputChange: (value: string) => void;
  onCustomExpectedChange: (value: string) => void;
  onCustomSkillChange: (value: string) => void;
  onProjectZipChange: (value: { name: string; base64: string }) => void;
  onCreateCustom: () => void;
};

export function ScenarioSelector({
  scenarios,
  selectedId,
  onSelect,
  onRun,
  customTitle,
  customTask,
  customInput,
  customExpected,
  customSkill,
  projectZipName,
  onCustomTitleChange,
  onCustomTaskChange,
  onCustomInputChange,
  onCustomExpectedChange,
  onCustomSkillChange,
  onProjectZipChange,
  onCreateCustom
}: Props) {
  const selected = scenarios.find((scenario) => scenario.scenario_id === selectedId);
  const isCustomDraft = selectedId === "__custom__";
  return (
    <section className="panel">
      <div className="panelHeader">
        <div>
          <h2>Scenario</h2>
          <p>Choose a scenario, or add your own logs.</p>
        </div>
        <button className="primaryButton" onClick={onRun} disabled={isCustomDraft} title="Run attempt">
          <Play size={16} />
          Run
        </button>
      </div>
      <select value={selectedId} onChange={(event) => onSelect(event.target.value)}>
        <option value="__custom__">Custom logs / project upload</option>
        {scenarios.map((scenario) => (
          <option key={scenario.scenario_id} value={scenario.scenario_id}>
            {scenario.title} ({scenario.purpose})
          </option>
        ))}
      </select>
      {isCustomDraft && (
        <CustomLogInput
          title={customTitle}
          task={customTask}
          inputText={customInput}
          expectedAnswer={customExpected}
          targetSkill={customSkill}
          projectZipName={projectZipName}
          onTitleChange={onCustomTitleChange}
          onTaskChange={onCustomTaskChange}
          onInputTextChange={onCustomInputChange}
          onExpectedAnswerChange={onCustomExpectedChange}
          onTargetSkillChange={onCustomSkillChange}
          onProjectZipChange={onProjectZipChange}
          onCreate={onCreateCustom}
        />
      )}
      {selected && !isCustomDraft && (
        <div className="logBlock">
          <strong>{selected.task}</strong>
          <pre>{selected.input_text}</pre>
          <p>Expected: {selected.expected_answer}</p>
          <p>Common mistake: {selected.common_mistake}</p>
        </div>
      )}
    </section>
  );
}
