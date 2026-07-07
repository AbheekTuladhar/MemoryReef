import { Brain, CheckCircle2, HelpCircle, Save } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api } from "./api";
import { AgentLogPanel } from "./components/AgentLogPanel";
import { AttemptResult } from "./components/AttemptResult";
import { ComparisonView } from "./components/ComparisonView";
import { ExperimentRunner } from "./components/ExperimentRunner";
import { ScenarioSelector } from "./components/ScenarioSelector";
import { SkillCard } from "./components/SkillCard";
import { SkillLibrary } from "./components/SkillLibrary";
import { TutorialModal } from "./components/TutorialModal";
import { TraceView } from "./components/TraceView";
import { AgentLog, ReflectionPayload, Scenario, Skill, Trace, VerificationPayload } from "./types";

type ReflectionState = {
  reflection: ReflectionPayload;
  proposed_skill: Skill;
  verification?: VerificationPayload;
};

export default function App() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [trace, setTrace] = useState<Trace | undefined>();
  const [agentLogs, setAgentLogs] = useState<AgentLog[]>([]);
  const [reflection, setReflection] = useState<ReflectionState | undefined>();
  const [comparison, setComparison] = useState<Parameters<typeof ComparisonView>[0]["comparison"]>();
  const [showTutorial, setShowTutorial] = useState(true);
  const [useSavedSkills, setUseSavedSkills] = useState(true);
  const [customTitle, setCustomTitle] = useState("");
  const [customTask, setCustomTask] = useState("Find the likely cause or next debugging step from these logs.");
  const [customInput, setCustomInput] = useState("");
  const [customExpected, setCustomExpected] = useState("");
  const [customSkill, setCustomSkill] = useState("Custom Debugging Lesson");
  const [projectZipName, setProjectZipName] = useState("");
  const [projectZipBase64, setProjectZipBase64] = useState("");
  const [status, setStatus] = useState("Ready");

  const selected = useMemo(
    () => scenarios.find((scenario) => scenario.scenario_id === selectedId),
    [scenarios, selectedId]
  );

  useEffect(() => {
    Promise.all([api.scenarios(), api.skills()]).then(([scenarioResponse, skillResponse]) => {
      setScenarios(scenarioResponse.scenarios);
      setSkills(skillResponse.skills);
      setSelectedId(scenarioResponse.scenarios[0]?.scenario_id ?? "");
    });
  }, []);

  async function refreshSkills() {
    const response = await api.skills();
    setSkills(response.skills);
  }

  async function refreshScenarios(selectId?: string) {
    const response = await api.scenarios();
    setScenarios(response.scenarios);
    if (selectId) {
      setSelectedId(selectId);
    }
  }

  async function createCustomScenario() {
    if (!customInput.trim() && !projectZipBase64) return;
    setStatus("Adding custom scenario");
    const response = await api.createCustomScenario({
      title: customTitle || "Custom Logs",
      task: customTask,
      input_text: customInput,
      expected_answer: customExpected || undefined,
      target_skill: customSkill || undefined,
      project_zip_base64: projectZipBase64 || undefined,
      project_zip_filename: projectZipName || undefined
    });
    await refreshScenarios(response.scenario.scenario_id);
    setTrace(undefined);
    setReflection(undefined);
    setAgentLogs([]);
    setComparison(undefined);
    setStatus("Custom scenario ready");
  }

  async function runAttempt() {
    if (!selectedId || selectedId === "__custom__") return;
    setStatus(useSavedSkills ? "Running investigator with saved skills" : "Running baseline investigator");
    setReflection(undefined);
    const response = await api.attempt(selectedId, useSavedSkills);
    setTrace(response.trace);
    setAgentLogs(response.trace.agent_logs ?? response.agent_logs ?? []);
    await refreshSkills();
    setStatus("Attempt complete");
  }

  async function runReflect() {
    if (!trace) return;
    setStatus("Reflecting on trace");
    const response = await api.reflect(trace.trace_id);
    setReflection(response);
    setAgentLogs((current) => [...current, ...(response.reflection.agent_logs ?? response.agent_logs ?? [])]);
    setStatus("Reflection complete");
  }

  async function runVerify() {
    if (!reflection) return;
    setStatus("Verifying skill");
    const response = await api.verifySkill(reflection.proposed_skill);
    setReflection({ ...reflection, verification: response });
    setAgentLogs((current) => [...current, ...(response.agent_logs ?? [])]);
    setStatus(`Verifier: ${response.status}`);
  }

  async function runSave() {
    if (reflection?.verification?.status === "rejected") {
      setStatus("Verifier rejected this skill; reflect again");
      return;
    }
    const skill = reflection?.verification?.final_skill ?? reflection?.proposed_skill;
    if (!skill) return;
    setStatus("Saving skill");
    await api.saveSkill(skill);
    await refreshSkills();
    setUseSavedSkills(true);
    setStatus("Skill saved; future runs can reuse it");
  }

  async function runCompare() {
    const scenarioId = selected?.paired_scenario_id ?? selectedId;
    if (!scenarioId) return;
    setStatus("Running before/after comparison");
    const response = await api.compare(scenarioId);
    setComparison(response);
    setAgentLogs(response.agent_logs ?? []);
    await refreshSkills();
    setStatus("Comparison complete");
  }

  return (
    <main>
      <TutorialModal open={showTutorial} onClose={() => setShowTutorial(false)} />
      <header className="appHeader">
        <div>
          <h1>LogLearner</h1>
          <p>Every attempt teaches the next one.</p>
        </div>
        <div className="headerActions">
          <button className="secondaryButton" onClick={() => setShowTutorial(true)} title="Open tutorial">
            <HelpCircle size={16} />
            Tutorial
          </button>
          <div className="statusPill">{status}</div>
        </div>
      </header>

      <section className="guideBand">
        <div>
          <span className="eyebrow">Demo recipe</span>
          <p>
            Start with a learning scenario, run the Investigator, reflect on the trace, verify and save Nemo's skill,
            then compare the paired test. You can also paste or upload your own logs and run the same flow.
          </p>
        </div>
        <label className="skillToggle">
          <input
            type="checkbox"
            checked={useSavedSkills}
            onChange={(event) => setUseSavedSkills(event.target.checked)}
          />
          <span>Run with saved skills</span>
        </label>
      </section>

      <section className="loopBar" aria-label="Learning loop">
        <span>Attempt</span>
        <span>Reflect</span>
        <span>Learn Skill</span>
        <span>Reuse</span>
      </section>

      <div className="workspace">
        <div className="leftColumn">
          <ScenarioSelector
            scenarios={scenarios}
            selectedId={selectedId}
            onSelect={setSelectedId}
            onRun={runAttempt}
            customTitle={customTitle}
            customTask={customTask}
            customInput={customInput}
            customExpected={customExpected}
            customSkill={customSkill}
            projectZipName={projectZipName}
            onCustomTitleChange={setCustomTitle}
            onCustomTaskChange={setCustomTask}
            onCustomInputChange={setCustomInput}
            onCustomExpectedChange={setCustomExpected}
            onCustomSkillChange={setCustomSkill}
            onProjectZipChange={({ name, base64 }) => {
              setProjectZipName(name);
              setProjectZipBase64(base64);
            }}
            onCreateCustom={createCustomScenario}
          />
          <AttemptResult trace={trace} />
          <TraceView trace={trace} />
          <AgentLogPanel logs={agentLogs} />
        </div>

        <div className="rightColumn">
          <section className="panel">
            <div className="panelHeader">
              <div>
                <h2>Reflection Agent</h2>
                <p>Extract one reusable lesson from the trace.</p>
              </div>
              <button className="secondaryButton" onClick={runReflect} disabled={!trace} title="Generate skill">
                <Brain size={16} />
                Reflect
              </button>
            </div>
            {!reflection ? (
              <p>No reflection yet.</p>
            ) : (
              <>
                <p>{reflection.reflection.what_happened}</p>
                <div className="confidenceMeter">
                  <span>Reflection confidence</span>
                  <strong>{Math.round(reflection.reflection.confidence * 100)}%</strong>
                </div>
                <p className="subtle">{reflection.reflection.lesson}</p>
                <SkillCard skill={reflection.proposed_skill} />
                <div className="buttonRow">
                  <button className="secondaryButton" onClick={runVerify} title="Verify skill">
                    <CheckCircle2 size={16} />
                    Verify
                  </button>
                  <button
                    className="primaryButton"
                    onClick={runSave}
                    disabled={reflection.verification?.status === "rejected"}
                    title="Save skill"
                  >
                    <Save size={16} />
                    Save
                  </button>
                </div>
                {reflection.verification && (
                  <p className={reflection.verification.status === "rejected" ? "warnText" : "successText"}>
                    Verifier confidence {Math.round(reflection.verification.confidence * 100)}%:{" "}
                    {reflection.verification.reason}
                  </p>
                )}
              </>
            )}
          </section>
          <SkillLibrary skills={skills} />
          <ComparisonView comparison={comparison} onCompare={runCompare} />
          <ExperimentRunner />
        </div>
      </div>
    </main>
  );
}
