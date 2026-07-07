import { FileArchive, FileUp, Plus } from "lucide-react";
import { ChangeEvent } from "react";

type Props = {
  title: string;
  task: string;
  inputText: string;
  expectedAnswer: string;
  targetSkill: string;
  projectZipName: string;
  onTitleChange: (value: string) => void;
  onTaskChange: (value: string) => void;
  onInputTextChange: (value: string) => void;
  onExpectedAnswerChange: (value: string) => void;
  onTargetSkillChange: (value: string) => void;
  onProjectZipChange: (value: { name: string; base64: string }) => void;
  onCreate: () => void;
};

export function CustomLogInput({
  title,
  task,
  inputText,
  expectedAnswer,
  targetSkill,
  projectZipName,
  onTitleChange,
  onTaskChange,
  onInputTextChange,
  onExpectedAnswerChange,
  onTargetSkillChange,
  onProjectZipChange,
  onCreate
}: Props) {
  async function handleFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    const text = await file.text();
    onInputTextChange(text);
    if (!title.trim()) {
      onTitleChange(file.name.replace(/\.[^.]+$/, ""));
    }
    event.target.value = "";
  }

  function readZip(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result ?? "");
      const base64 = result.includes(",") ? result.split(",")[1] : result;
      onProjectZipChange({ name: file.name, base64 });
      if (!title.trim()) {
        onTitleChange(file.name.replace(/\.[^.]+$/, ""));
      }
    };
    reader.readAsDataURL(file);
    event.target.value = "";
  }

  return (
    <section className="customPanel">
      <div className="panelHeader">
        <div>
          <h2>Use Your Own Logs</h2>
          <p>Paste logs, upload a log file, or attach a zipped project for more context.</p>
        </div>
        <div className="uploadActions">
          <label className="fileButton" title="Upload log file">
            <FileUp size={16} />
            Logs
            <input type="file" accept=".log,.txt,.json,.csv,.md" onChange={handleFile} />
          </label>
          <label className="fileButton" title="Attach project zip">
            <FileArchive size={16} />
            Project ZIP
            <input type="file" accept=".zip,application/zip" onChange={readZip} />
          </label>
        </div>
      </div>

      <div className="formGrid">
        <label>
          Scenario title
          <input value={title} onChange={(event) => onTitleChange(event.target.value)} placeholder="Checkout outage logs" />
        </label>
        <label>
          Target skill name
          <input
            value={targetSkill}
            onChange={(event) => onTargetSkillChange(event.target.value)}
            placeholder="Investigate checkout failures"
          />
        </label>
      </div>
      <label className="fullField">
        Task
        <input value={task} onChange={(event) => onTaskChange(event.target.value)} />
      </label>
      <label className="fullField">
        Logs or project notes
        <textarea
          value={inputText}
          onChange={(event) => onInputTextChange(event.target.value)}
          placeholder="Paste timestamps, stack traces, deployment notes, or dependency errors here."
        />
      </label>
      {projectZipName && (
        <div className="attachedZip">
          <FileArchive size={16} />
          <span>Attached project context: {projectZipName}</span>
        </div>
      )}
      <label className="fullField">
        Expected answer, optional
        <input
          value={expectedAnswer}
          onChange={(event) => onExpectedAnswerChange(event.target.value)}
          placeholder="Only needed if you want matched-expected scoring"
        />
      </label>
      <button className="primaryButton" onClick={onCreate} disabled={!inputText.trim() && !projectZipName} title="Create custom scenario">
        <Plus size={16} />
        Add Custom Scenario
      </button>
    </section>
  );
}
