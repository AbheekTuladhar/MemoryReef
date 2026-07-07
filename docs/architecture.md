# MemoryReef — Architecture

This document describes how MemoryReef works end to end: the learning loop, the three agents and the exact tools each runs, the data model, the JSON storage layout, the HTTP API, the research harness, and how the frontend and backend are wired together.

For the narrative and the headline result, see the [README](../README.md). This document is the engineering reference.

---

## 1. The learning loop

MemoryReef turns a single debugging attempt into a reusable skill, then reuses that skill on the next similar task.

```
                         backend/data/scenarios.json
                                    │
                                    ▼
   ┌──────────┐  trace   ┌───────────┐  proposed skill  ┌───────────┐
   │  Dory    │─────────▶│   Nemo    │─────────────────▶│  Puffer   │
   │ attempt  │          │  reflect  │                  │  verify   │
   └────┬─────┘          └───────────┘                  └─────┬─────┘
        │                                                     │ approved
        │                                                     ▼
        │                                            ┌──────────────────┐
        │◀────────── retrieve on similar task ───────│  Skill library   │
        │                                            │  (the "reef")    │
        ▼                                            └──────────────────┘
   right answer,
   higher confidence
```

Step by step:

1. **Attempt** (`POST /api/attempt`) — Dory investigates a scenario and produces an `AttemptTrace` with a `FinalAnswer`. The trace is redacted and persisted.
2. **Reflect** (`POST /api/reflect`) — Nemo reads a stored trace and proposes one `Skill` (plus a `Reflection` record).
3. **Verify** (`POST /api/verify-skill`) — Puffer returns a `Verification` (`approved` / `revised` / `rejected`).
4. **Save** (`POST /api/save-skill`) — an approved skill is written to the library with `status="approved"`.
5. **Reuse** (`POST /api/attempt` with `use_skills=true`, or `POST /api/compare`) — Dory retrieves relevant approved skills and re-solves a paired scenario, now correctly.

The `compare` endpoint runs steps 1 and 5 back-to-back on the same scenario (without-skill vs. with-skill) so the UI can show the before/after in a single call.

---

## 2. The agents and their tools

All three agents live in `backend/agents/`. Their names are constants in `backend/agents/__init__.py` (`Dory`, `Nemo`, `Puffer`). Every agent emits summarized `AgentLog` entries — these are *activity logs*, not hidden chain-of-thought.

The agents are **real [Google ADK](https://google.github.io/adk-docs/) `LlmAgent`s backed by Gemini.** Each wrapper function (`run_investigation`, `reflect_on_trace`, `verify_skill`) keeps its original signature and return type, but internally builds an `LlmAgent`, prompts it, and parses structured JSON back.

### The ADK runtime (`agents/adk_runtime.py`)

This module is the LLM core. It contains:

- **Three agent factories** — `build_dory()`, `build_nemo()`, `build_puffer()`. Each returns an `LlmAgent(name=…, model=MODEL, instruction=<persona>, output_schema=<schema>, generate_content_config=temperature 0.1)`. The persona instruction carries the fixed rules; per-run specifics (logs, retrieved skill, trace) travel in the prompt.
- **Three flat Pydantic `output_schema`s** — `DoryOutput` (`root_cause`, `confidence`, `reasoning`, `evidence[]`, `next_checks[]`), `NemoOutput` (`reflection_summary`, `lesson`, `skill: ProposedSkill`), `PufferOutput` (`status`, `reason`, `revised_fields`). Setting `output_schema` forces Gemini to return JSON that parses with `Model.model_validate_json`, which is what keeps the whole loop machine-readable.
- **The single LLM boundary, `run_agent(agent, prompt) -> str`.** Every model call in the product goes through this one function. It spins up an `InMemoryRunner`, creates a session, sends the prompt as a `types.Content`, iterates events, and returns the final response text. Because tests monkeypatch this one seam, the entire loop runs offline with canned JSON and no config flag or deterministic fallback in the real path.

**Sync/async bridging.** ADK's `session_service.create_session` is async, but the FastAPI endpoints are synchronous (`def`, run in a threadpool, so there's no running event loop). `run_agent` therefore calls `asyncio.run(...)` to create the session, then drives the *synchronous* `runner.run(...)` generator to collect the final event. This keeps the agent call a plain blocking function the endpoints can call directly.

**Why tools feed the prompt instead of being ADK function-tools.** The agents do **not** register the Python tools (redactor / keyword / timeline) as ADK function-tools. `output_schema` + `tools` is not reliably supported together on current Gemini models — asking for both structured output *and* tool-calling degrades the structured output. So we run the small deterministic tools ourselves and inject their results into the prompt; the LLM still makes the actual root-cause / reflection / verify **decision**, but its output stays reliably structured. Native tool-calling is a documented next step.

### Dory — Investigator (`agents/investigator.py`, `run_investigation`)

Solves the current debugging task and leaves a trace behind. It first runs the Python tools to build the `TraceStep`s the UI shows, then asks the Dory `LlmAgent` for the decision:

| Tool | Module | What it does |
| --- | --- | --- |
| Redactor | `tools/redactor.py` (`redact_text`) | Strips secret-like values *before* anything is stored or sent to Gemini. |
| Keyword pattern tool | `tools/keyword_pattern_tool.py` (`detect_keywords`) | Detects incident hints (deployment, retry, resource, etc.). |
| Timeline tool | `tools/timeline_tool.py` (`build_timeline`) | Orders events and finds the earliest abnormal clue. |
| Skill retriever | `tools/skill_retriever.py` (`retrieve_skills_for_scenario`) | Pulls relevant approved skills (only when `use_skills=true`). |
| Skill store | `tools/skill_store.py` (`increment_usage`) | Bumps `usage_count` on any skill applied. |

Prompt shaping (both prompts are real Gemini calls; the difference is what goes into them):
- **Without skills** → `_naive_prompt`: Gemini sees only the redacted logs and is told to give a fast, frequency-driven guess. It reliably falls for the loudest / most repeated error, at modest confidence (≈ 0.60).
- **With skills** → `_skilled_prompt`: the retrieved skill's lesson + steps + anti-pattern and the time-ordered timeline (with the earliest abnormal event called out) are injected. Gemini reaches the correct upstream root cause at higher confidence (≈ 0.80–0.90).
- Low temperature (0.1) keeps this wrong→right beat stable across takes.
- `_matches_expected` decides `matched_expected` by term overlap with the expected answer, with a guard so answers that start with the "loudest" component (`gateway` / `frontend` / `api service`) don't count as correct.

Output: an `AttemptTrace` (steps + agent logs + `FinalAnswer` built from `DoryOutput` + `matched_expected`).

### Nemo — Reflection (`agents/reflection.py`, `reflect_on_trace`)

Does *not* solve the original task. It builds a prompt from the finished trace (steps, the answer, the expected answer, and whether it matched) and asks the Nemo `LlmAgent` to distill one reusable, procedural, service-agnostic lesson.

- **Name steering:** the prompt tells Gemini the lesson is best described as the scenario's `target_skill` and to name the skill exactly that (or a close variant keeping its key words), so the learning loop stays coherent while the content is still LLM-authored.
- Parses `NemoOutput`, wraps the `ProposedSkill` into a `Skill` with a fresh id and `status="proposed"`, and returns a `Reflection` (`reflection_summary`, `lesson`, proposed skill id, confidence, agent logs) plus that `Skill`.

### Puffer — Verifier (`agents/verifier.py`, `verify_skill`)

The quality-and-safety gate. **Hard deterministic Python guards run first and are never delegated to the LLM**; only skills that clear them reach the Puffer `LlmAgent`, which makes the nuanced usefulness/generality judgement. Order:

1. **Reject — secret-like content (Python).** A regex (`SECRETISH`: `@`, `password`/`passwd`, `api_key`, `token=`, `secret=`, or any 32+ char blob) scans name + description + steps + when-to-use. Match → `rejected`.
2. **Revise — too thin (Python).** Description under 8 words *or* fewer than 3 steps → `revised`.
3. **Reject — duplicate (Python).** If the skill's last-three-tags signature already exists in the library → `rejected` (this feeds the harness's "duplicate skill rejections" metric).
4. **LLM verdict (Puffer `LlmAgent`).** For skills that clear the guards, Gemini returns `approved` / `revised` / `rejected` with a reason. On `revised`, only whitelisted plain-string fields (`name`, `description`, `anti_pattern`) from `revised_fields` are applied, so the LLM can never inject a string where the schema expects a list. Anything not explicitly rejected/revised defaults to `approved`.

`/api/save-skill` force-sets `status="approved"` on write, so only vetted skills reach the reef.

### Configuration & credentials (`backend/config.py`, `.env`)

`config.py` loads the git-ignored repo-root `.env` once at import time via `python-dotenv` (`override=False`, so already-exported vars win) and exposes `MODEL = os.getenv("MEMORYREEF_MODEL", …)`. It never reads or prints secret values — backend selection is env-only and handled by `google-genai` itself.

Two backends, selected in `.env` (see `.env.example`):

| Backend | Env |
| --- | --- |
| **Google AI Studio** | `GOOGLE_GENAI_USE_VERTEXAI=FALSE` + `GOOGLE_API_KEY` |
| **Vertex AI** | `GOOGLE_GENAI_USE_VERTEXAI=TRUE` + `GOOGLE_CLOUD_PROJECT` + `GOOGLE_CLOUD_LOCATION` |

Vertex auth uses Application Default Credentials (`gcloud auth application-default login` + `... set-quota-project <project>`), and the Vertex AI API must be enabled on the project.

> **Location gotcha:** `gemini-flash-latest` / Gemini 3.x models are only served from `GOOGLE_CLOUD_LOCATION=global` on Vertex. A regional location such as `us-central1` returns **404** for these models.

---

## 3. Data model

Defined in `backend/models.py` (Pydantic v2). Core entities:

**`Scenario`** — one incident.
`scenario_id`, `title`, `pair_id`, `purpose` (`learn` | `test` | `custom`), `task`, `input_text` (the log snippet), `expected_answer`, `common_mistake`, `target_skill`, `paired_scenario_id`. Scenarios come in learn/test pairs sharing a `pair_id`.

**`AttemptTrace`** — the record of one investigation.
`trace_id`, `scenario_id`, `used_skills[]`, `steps[]` (`TraceStep`: step / action / observation / reasoning_summary), `agent_logs[]` (`AgentLog`), `final_answer` (`FinalAnswer`: `likely_cause`, `confidence`, `evidence[]`, `next_checks[]`), `matched_expected`.

**`Skill`** — a stored "pearl."
`skill_id`, `name`, `description`, `when_to_use[]`, `steps[]`, `anti_pattern`, `source_trace_id`, `tags[]`, `usage_count`, and a **status lifecycle**:

```
proposed ──▶ approved     (Puffer OK, saved to the reef)
   │    └──▶ rejected      (secret-like or duplicate; not saved)
   └───────▶ revised       (renamed or fleshed out, then saveable)
```

**`Reflection`** — Nemo's output: `reflection_id`, `trace_id`, `what_happened`, `lesson`, `proposed_skill_id`, `confidence`, `agent_logs[]`.

**`Verification`** — Puffer's output: `status` (`approved`/`revised`/`rejected`), `reason`, `final_skill`, `confidence`, `agent_logs[]`.

**Experiment types** — `ExperimentRequest` (config + ablation flags), `ExperimentConditionResult`, `ExperimentScenarioResult`, `ExperimentMetricSummary`, `ExperimentRun`. Request/response wrappers: `AttemptRequest`, `TraceRequest`, `SkillRequest`, `CompareRequest`, `CustomScenarioRequest`.

### Storage layout — `backend/data/`

Flat JSON files (via `tools/json_store.py`; `DATA_DIR` points here). No database.

| File | Contents |
| --- | --- |
| `scenarios.json` | The 4 curated learn/test scenario pairs. |
| `custom_scenarios.json` | User-uploaded scenarios. |
| `skills.json` | The skill library (the "reef"). |
| `traces.json` | All saved attempt traces. |
| `experiment_config.json` | Experiment definition: conditions + scenario pairs + hypothesis. |
| `experiment_runs.json` | Full structured history of every experiment run. |
| `experiment_results.csv` | Row-level per-condition results (exportable). |
| `paper_summary.md` | Generated Markdown research summary (method, metrics, examples, limitations). |

---

## 4. API surface

FastAPI app in `backend/main.py`, titled `MemoryReef API`. All endpoints under `/api`.

| Method & path | Description |
| --- | --- |
| `GET /` | Health/info root. |
| `GET /api` | Lists available endpoints. |
| `GET /api/scenarios` | All curated scenarios. |
| `POST /api/custom-scenarios` | Create a scenario from pasted logs or an uploaded project zip. |
| `POST /api/attempt` | Dory investigates a scenario (`use_skills` toggles retrieval); saves and returns the trace. |
| `POST /api/reflect` | Nemo reflects on a stored trace; returns a reflection + proposed skill. |
| `POST /api/verify-skill` | Puffer verifies a proposed skill; returns approve/revise/reject. |
| `POST /api/save-skill` | Persist an approved skill to the library. |
| `GET /api/skills` | The current skill library. |
| `POST /api/compare` | Run the test scenario without-skill vs. with-skill; returns both traces + an `improved` / `confidence_delta` verdict. |
| `GET /api/experiments/config` | The experiment configuration. |
| `POST /api/experiments/run` | Run the full experiment (conditions + ablations); returns the run and writes artifacts. |
| `GET /api/experiments/latest` | The most recent saved experiment run. |
| `GET /api/experiments/export/csv` | Download `experiment_results.csv`. |
| `GET /api/experiments/export/summary` | Download the generated `paper_summary.md`. |

---

## 5. Research / experiment harness

Lives in `backend/experiments/` (`runner.py`, `metrics.py`, `persistence.py`). Driven by `POST /api/experiments/run` with an `ExperimentRequest`.

**Conditions** (per scenario pair):

| Condition | What runs |
| --- | --- |
| `baseline` | Test scenario, **no** skills. |
| `learning` | Run the *learn* scenario → Nemo reflects → Puffer verifies → save the skill. |
| `reuse` | Test scenario **with** relevant learned-skill retrieval. |
| `random_skill` | Test scenario with a deliberately **unrelated** skill — the control that isolates whether the gain comes from the *relevant* lesson vs. just extra prompt text. |

**Ablation flags** (on the request) let you turn individual mechanisms on/off:
`verifier_enabled`, `reflection_enabled`, `skill_retrieval_enabled`, `duplicate_filtering_enabled`, `random_skill_control_enabled`, and `persist_experiment_skills_to_main_library`.

**Isolation & reproducibility:** `run_experiment` **snapshots** the live skill library, empties it, runs the conditions on a clean slate, and — unless `persist_experiment_skills_to_main_library` is set — **restores** the snapshot in a `finally` block. So experiments never pollute the demo's skill library. Each run records skill counts before/after, the config id, and a timestamp.

**Metrics** (`metrics.py` → `ExperimentMetricSummary`): accuracy by condition, matched-expected counts, mean confidence by condition, confidence delta per pair, an evidence-quality proxy (cited-evidence count), skill-retrieval success rate, Puffer approval rate, improvement rate (pairs where baseline was wrong and reuse was right), overconfident-wrong-answer count, and duplicate-skill rejections.

**Outputs** (`persistence.py` → `save_experiment_artifacts`): appends to `experiment_runs.json`, writes `experiment_results.csv`, and regenerates `paper_summary.md`. The committed summary reports **baseline 0.0 / reuse 1.0** accuracy and an improvement rate of **1.0** across all 4 pairs.

---

## 6. Frontend ↔ backend wiring

- **Backend:** FastAPI on **`http://127.0.0.1:8000`** (`uv run uvicorn backend.main:app --reload`, or via the dual launcher).
- **Frontend:** React + Vite on **`http://127.0.0.1:5173`** (`npm run dev`).
- **No proxy.** The React app calls the backend directly. The backend enables **CORS** for exactly the two frontend origins (`localhost:5173` and `127.0.0.1:5173`) via `CORSMiddleware`.
- **Dual launcher:** `uv run memoryreef` maps to `backend.dev:run` (see `pyproject.toml` `[project.scripts]`). It installs frontend deps on first run (`npm ci` if a lockfile exists, else `npm install`), starts both processes, and tears them down together on Ctrl-C. Host/port are overridable via `MEMORYREEF_HOST`, `MEMORYREEF_PORT`, `MEMORYREEF_FRONTEND_PORT`.

A configured `.env` (AI Studio or Vertex — see §2) is required to run the app, since the agents make real Gemini calls. The end-to-end test suite, however, mocks the single `run_agent` boundary and runs fully offline with no credentials — see `backend/tests/conftest.py`.
