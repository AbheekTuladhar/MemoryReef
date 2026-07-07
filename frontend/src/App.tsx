import { Brain, CheckCircle2, HelpCircle, Loader2, Play, Save } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api } from "./api";
import { AgentLogPanel } from "./components/AgentLogPanel";
import { AttemptResult } from "./components/AttemptResult";
import { ComparisonView } from "./components/ComparisonView";
import { Fish, FishKind } from "./components/Fish";
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

// Loop stages, shared by the top loop bar and the handlers that light them up.
const LOOP_STEPS = ["Attempt", "Reflect", "Learn skill", "Reuse"];

// Fish avatar per loop step: Dory attempts, Nemo reflects, Puffer verifies the
// pearl, and Dory returns to reuse what the reef learned.
const LOOP_FISH: FishKind[] = ["dory", "nemo", "puffer", "dory"];

// Signature "Loudest Error Trap": Dory blames 50 Redis timeouts, the real cause is DB pool exhaustion.
const DEMO_SCENARIO_ID = "loudest_error_1a";

const wait = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

// Which real (slow) call is currently in flight, so we can show a per-agent "thinking" state.
type BusyAction = "attempt" | "reflect" | "verify" | "save" | "compare";

const errMessage = (err: unknown) => (err instanceof Error ? err.message : String(err));

// Ocean-themed "the agent is actually working" caption for the active loop step.
const THINKING_TEXT: Record<BusyAction, string> = {
  attempt: "Dory is investigating…",
  reflect: "Nemo is reflecting…",
  verify: "Puffer is verifying…",
  save: "Saving the pearl…",
  compare: "Replaying with the reef's memory…"
};

export default function App() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [trace, setTrace] = useState<Trace | undefined>();
  const [agentLogs, setAgentLogs] = useState<AgentLog[]>([]);
  const [reflection, setReflection] = useState<ReflectionState | undefined>();
  const [comparison, setComparison] = useState<Parameters<typeof ComparisonView>[0]["comparison"]>();
  const [showTutorial, setShowTutorial] = useState(false);
  const [useSavedSkills, setUseSavedSkills] = useState(true);
  const [customTitle, setCustomTitle] = useState("");
  const [customTask, setCustomTask] = useState("Find the likely cause or next debugging step from these logs.");
  const [customInput, setCustomInput] = useState("");
  const [customExpected, setCustomExpected] = useState("");
  const [customSkill, setCustomSkill] = useState("Custom Debugging Lesson");
  const [projectZipName, setProjectZipName] = useState("");
  const [projectZipBase64, setProjectZipBase64] = useState("");
  const [status, setStatus] = useState("Ready");
  const [activeStep, setActiveStep] = useState(-1);
  const [isDemo, setIsDemo] = useState(false);
  const [newSkillId, setNewSkillId] = useState<string | undefined>();
  const [busy, setBusy] = useState<BusyAction | null>(null);
  const [error, setError] = useState<string | undefined>();

  // Lock every control while any real call is running (or the demo is auto-playing).
  const anyBusy = busy !== null || isDemo;

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
    setActiveStep(-1);
    setStatus("Custom scenario ready");
  }

  // Each handler accepts optional explicit inputs and returns its result, so both the
  // click handlers (no args -> read state) and the demo sequencer (chained args) can use them.
  async function runAttempt(useSkillsArg = useSavedSkills, scenarioIdArg = selectedId) {
    if (!scenarioIdArg || scenarioIdArg === "__custom__") return;
    setBusy("attempt");
    setError(undefined);
    setActiveStep(0);
    setStatus(useSkillsArg ? "Dory retries with saved skills…" : "Dory investigates the logs…");
    setReflection(undefined);
    try {
      const response = await api.attempt(scenarioIdArg, useSkillsArg);
      setTrace(response.trace);
      setAgentLogs(response.trace.agent_logs ?? response.agent_logs ?? []);
      await refreshSkills();
      setStatus("Attempt complete");
      return response.trace;
    } catch (err) {
      setError(`Dory could not finish the attempt: ${errMessage(err)}`);
      setStatus("Attempt failed");
      return undefined;
    } finally {
      setBusy(null);
    }
  }

  async function runReflect(traceArg = trace) {
    if (!traceArg) return;
    setBusy("reflect");
    setError(undefined);
    setActiveStep(1);
    setStatus("Nemo reflects on the trace…");
    try {
      const response = await api.reflect(traceArg.trace_id);
      setReflection(response);
      setAgentLogs((current) => [...current, ...(response.reflection.agent_logs ?? response.agent_logs ?? [])]);
      setStatus("Nemo distilled a pearl");
      return response as ReflectionState;
    } catch (err) {
      setError(`Nemo could not reflect: ${errMessage(err)}`);
      setStatus("Reflection failed");
      return undefined;
    } finally {
      setBusy(null);
    }
  }

  async function runVerify(reflectionArg = reflection) {
    if (!reflectionArg) return;
    setBusy("verify");
    setError(undefined);
    setActiveStep(2);
    setStatus("Puffer checks the pearl…");
    try {
      const response = await api.verifySkill(reflectionArg.proposed_skill);
      setReflection({ ...reflectionArg, verification: response });
      setAgentLogs((current) => [...current, ...(response.agent_logs ?? [])]);
      setStatus(`Puffer: ${response.status}`);
      return response;
    } catch (err) {
      setError(`Puffer could not verify the pearl: ${errMessage(err)}`);
      setStatus("Verification failed");
      return undefined;
    } finally {
      setBusy(null);
    }
  }

  async function runSave(reflectionArg = reflection, verificationArg = reflection?.verification) {
    if (verificationArg?.status === "rejected") {
      setStatus("Puffer rejected this pearl; ask Nemo to reflect again");
      return;
    }
    const skill = verificationArg?.final_skill ?? reflectionArg?.proposed_skill;
    if (!skill) return;
    setBusy("save");
    setError(undefined);
    setActiveStep(2);
    setStatus("Saving the pearl to the reef…");
    try {
      await api.saveSkill(skill);
      setNewSkillId(skill.skill_id);
      await refreshSkills();
      setUseSavedSkills(true);
      setStatus("Pearl saved to the reef");
      return skill;
    } catch (err) {
      setError(`Could not save the pearl: ${errMessage(err)}`);
      setStatus("Save failed");
      return undefined;
    } finally {
      setBusy(null);
    }
  }

  async function runCompare(scenarioIdArg?: string) {
    const scenarioId = scenarioIdArg ?? selected?.paired_scenario_id ?? selectedId;
    if (!scenarioId) return;
    setBusy("compare");
    setError(undefined);
    setActiveStep(3);
    setStatus("Replaying the paired test with the reef's memory…");
    try {
      const response = await api.compare(scenarioId);
      setComparison(response);
      setAgentLogs(response.agent_logs ?? []);
      await refreshSkills();
      setStatus("Comparison complete");
      return response;
    } catch (err) {
      setError(`The before / after replay failed: ${errMessage(err)}`);
      setStatus("Comparison failed");
      return undefined;
    } finally {
      setBusy(null);
    }
  }

  // Auto-play: reset, then stage the whole loop with pauses so each reveal lands on camera.
  // Idempotent enough to re-run for multiple takes because it resets state up front.
  async function runDemo() {
    if (isDemo) return;
    const demo =
      scenarios.find((scenario) => scenario.scenario_id === DEMO_SCENARIO_ID) ??
      scenarios.find((scenario) => scenario.purpose === "learn") ??
      scenarios[0];
    if (!demo) return;

    // Reset everything up front so the demo is re-runnable for multiple video takes.
    setIsDemo(true);
    setShowTutorial(false);
    setTrace(undefined);
    setReflection(undefined);
    setComparison(undefined);
    setAgentLogs([]);
    setNewSkillId(undefined);
    setActiveStep(-1);
    setError(undefined);
    setSelectedId(demo.scenario_id);
    setUseSavedSkills(false);

    // The real API calls now provide the pauses themselves (~2-6s of genuine agent work),
    // so we only add tiny beats between reveals for visual clarity. If any step fails, the
    // handler surfaces an inline error and returns undefined, and we stop the sequence.
    try {
      const attempted = await runAttempt(false, demo.scenario_id);
      if (!attempted) return;
      await wait(400);
      const reflected = await runReflect(attempted);
      if (!reflected) return;
      await wait(400);
      const verified = await runVerify(reflected);
      await wait(400);
      await runSave(reflected, verified);
      await wait(500);
      await runCompare(demo.paired_scenario_id ?? demo.scenario_id);
    } finally {
      setIsDemo(false);
    }
  }

  return (
    <main>
      <TutorialModal open={showTutorial} onClose={() => setShowTutorial(false)} />
      <header className="appHeader">
        <div className="brand">
          <span className="brandMark" aria-hidden="true">
            🪸
          </span>
          <div>
            <h1>MemoryReef</h1>
            <p>Every attempt teaches the next one.</p>
          </div>
        </div>
        <div className="headerActions">
          <button
            className="demoButton"
            onClick={runDemo}
            disabled={isDemo || scenarios.length === 0}
            title="Auto-play the full learning loop"
          >
            <Play size={18} />
            {isDemo ? "Playing demo…" : "Play demo"}
          </button>
          <button className="secondaryButton" onClick={() => setShowTutorial(true)} title="Open tutorial">
            <HelpCircle size={16} />
            Tutorial
          </button>
          <div className="statusPill" aria-live="polite">
            {status}
          </div>
        </div>
      </header>

      <section className="guideBand">
        <div>
          <span className="eyebrow">Demo recipe</span>
          <p>
            Start with a learning scenario, run Dory, let Nemo reflect on the trace, have Puffer verify and save the skill,
            then compare the paired test. Or just hit <strong>Play demo</strong> and watch the reef learn.
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
        {LOOP_STEPS.map((label, index) => (
          <div
            key={label}
            className={`loopStep${index === activeStep ? " active" : ""}${index < activeStep ? " done" : ""}`}
          >
            <span className="loopIndex">
              <Fish kind={LOOP_FISH[index]} bob={busy !== null && index === activeStep} />
              {index < activeStep && (
                <span className="loopDone" aria-hidden="true">
                  ✓
                </span>
              )}
            </span>
            <span className="loopText">
              <span className="loopLabel">{label}</span>
              {busy && index === activeStep && <span className="loopThinking">{THINKING_TEXT[busy]}</span>}
            </span>
          </div>
        ))}
      </section>

      {error && (
        <div className="errorBanner" role="alert">
          <span>{error}</span>
          <button onClick={() => setError(undefined)} title="Dismiss">
            Dismiss
          </button>
        </div>
      )}

      <div className="workspace">
        <div className="leftColumn">
          <ScenarioSelector
            scenarios={scenarios}
            selectedId={selectedId}
            onSelect={setSelectedId}
            onRun={() => runAttempt()}
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
            running={busy === "attempt"}
            disabled={anyBusy}
          />
          <AttemptResult trace={trace} />
          <TraceView trace={trace} />
          <AgentLogPanel logs={agentLogs} />
        </div>

        <div className="rightColumn">
          <ComparisonView
            comparison={comparison}
            onCompare={() => runCompare()}
            running={busy === "compare"}
            disabled={anyBusy}
          />
          <section className="panel">
            <div className="panelHeader">
              <div>
                <h2>Nemo reflects</h2>
                <p>Extract one reusable lesson from Dory's trace.</p>
              </div>
              <button
                className="secondaryButton"
                onClick={() => runReflect()}
                disabled={!trace || anyBusy}
                title="Generate skill"
              >
                {busy === "reflect" ? <Loader2 size={16} className="spin" /> : <Brain size={16} />}
                {busy === "reflect" ? "Reflecting…" : "Reflect"}
              </button>
            </div>
            {!reflection ? (
              <p className="subtle">No reflection yet.</p>
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
                  <button
                    className="secondaryButton"
                    onClick={() => runVerify()}
                    disabled={anyBusy}
                    title="Verify skill"
                  >
                    {busy === "verify" ? <Loader2 size={16} className="spin" /> : <CheckCircle2 size={16} />}
                    {busy === "verify" ? "Verifying…" : "Verify"}
                  </button>
                  <button
                    className="primaryButton"
                    onClick={() => runSave()}
                    disabled={anyBusy || reflection.verification?.status === "rejected"}
                    title="Save skill"
                  >
                    {busy === "save" ? <Loader2 size={16} className="spin" /> : <Save size={16} />}
                    {busy === "save" ? "Saving…" : "Save"}
                  </button>
                </div>
                {reflection.verification && (
                  <p className={reflection.verification.status === "rejected" ? "warnText" : "successText"}>
                    Puffer confidence {Math.round(reflection.verification.confidence * 100)}%:{" "}
                    {reflection.verification.reason}
                  </p>
                )}
              </>
            )}
          </section>
          <SkillLibrary skills={skills} newSkillId={newSkillId} />
          <ExperimentRunner />
        </div>
      </div>
    </main>
  );
}
