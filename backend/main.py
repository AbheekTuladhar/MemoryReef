from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.agents.investigator import run_investigation
from backend.agents.reflection import reflect_on_trace
from backend.agents.verifier import verify_skill
from backend.experiments.runner import load_experiment_config, run_experiment
from backend.models import AttemptRequest, CompareRequest, CustomScenarioRequest, ExperimentRequest, SkillRequest, TraceRequest
from backend.tools.json_store import DATA_DIR, read_json
from backend.tools.project_zip_tool import summarize_project_zip
from backend.tools.scenario_store import get_scenario, load_scenarios, save_custom_scenario
from backend.tools.skill_retriever import retrieve_skills_for_scenario
from backend.tools.skill_store import load_skills, save_skill
from backend.tools.trace_store import get_trace, save_trace


app = FastAPI(title="LogLearner API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict[str, object]:
    return {
        "name": "LogLearner API",
        "status": "ok",
        "message": "Use /api for available endpoints. The frontend runs at http://127.0.0.1:5173/.",
    }


@app.get("/api")
def api_index() -> dict[str, object]:
    return {
        "status": "ok",
        "endpoints": [
            "GET /api/scenarios",
            "POST /api/custom-scenarios",
            "POST /api/attempt",
            "POST /api/reflect",
            "POST /api/verify-skill",
            "POST /api/save-skill",
            "GET /api/skills",
            "POST /api/compare",
            "GET /api/experiments/config",
            "POST /api/experiments/run",
            "GET /api/experiments/latest",
            "GET /api/experiments/export/csv",
            "GET /api/experiments/export/summary",
        ],
        "note": "Agent logs are summarized activity logs, not hidden chain-of-thought.",
    }


@app.get("/api/scenarios")
def scenarios() -> dict[str, object]:
    return {"scenarios": [scenario.model_dump() for scenario in load_scenarios()]}


@app.post("/api/custom-scenarios")
def custom_scenario(request: CustomScenarioRequest) -> dict[str, object]:
    project = summarize_project_zip(request.project_zip_base64, request.project_zip_filename)
    combined_input = request.input_text.strip()
    if project["context"]:
        combined_input = f"{combined_input}\n\n{project['context']}" if combined_input else str(project["context"])
    if not combined_input.strip():
        raise HTTPException(status_code=400, detail="input_text or project_zip_base64 is required")
    scenario = save_custom_scenario(
        title=request.title,
        task=request.task,
        input_text=combined_input,
        expected_answer=request.expected_answer,
        target_skill=request.target_skill,
    )
    return {"scenario": scenario.model_dump(), "project_summary": project}


@app.post("/api/attempt")
def attempt(request: AttemptRequest) -> dict[str, object]:
    try:
        scenario = get_scenario(request.scenario_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    skills = retrieve_skills_for_scenario(scenario) if request.use_skills else []
    trace = save_trace(run_investigation(scenario, skills))
    return {
        "trace": trace.model_dump(),
        "answer": trace.final_answer.model_dump(),
        "skills_used": [skill.model_dump() for skill in skills],
        "agent_logs": [log.model_dump() for log in trace.agent_logs],
    }


@app.post("/api/reflect")
def reflect(request: TraceRequest) -> dict[str, object]:
    try:
        trace = get_trace(request.trace_id)
        scenario = get_scenario(trace.scenario_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    reflection, proposed_skill = reflect_on_trace(trace, scenario)
    return {
        "reflection": reflection.model_dump(),
        "proposed_skill": proposed_skill.model_dump(),
        "agent_logs": [log.model_dump() for log in reflection.agent_logs],
    }


@app.post("/api/verify-skill")
def verify(request: SkillRequest) -> dict[str, object]:
    verification = verify_skill(request.skill)
    return verification.model_dump()


@app.post("/api/save-skill")
def save(request: SkillRequest) -> dict[str, object]:
    skill = request.skill.model_copy(update={"status": "approved"})
    return {"skill": save_skill(skill).model_dump()}


@app.get("/api/skills")
def skills() -> dict[str, object]:
    return {"skills": [skill.model_dump() for skill in load_skills()]}


@app.get("/api/experiments/config")
def experiment_config() -> dict[str, object]:
    return load_experiment_config()


@app.post("/api/experiments/run")
def experiment_run(request: ExperimentRequest) -> dict[str, object]:
    run = run_experiment(request)
    return {"run": run.model_dump()}


@app.get("/api/experiments/latest")
def experiment_latest() -> dict[str, object]:
    runs = read_json("experiment_runs.json", [])
    if not runs:
        raise HTTPException(status_code=404, detail="No experiment runs have been saved yet.")
    return {"run": runs[-1]}


@app.get("/api/experiments/export/csv")
def experiment_export_csv() -> FileResponse:
    path = DATA_DIR / "experiment_results.csv"
    if not path.exists():
        raise HTTPException(status_code=404, detail="No CSV export exists yet.")
    return FileResponse(path, media_type="text/csv", filename="experiment_results.csv")


@app.get("/api/experiments/export/summary")
def experiment_export_summary() -> FileResponse:
    path = DATA_DIR / "paper_summary.md"
    if not path.exists():
        raise HTTPException(status_code=404, detail="No paper summary exists yet.")
    return FileResponse(path, media_type="text/markdown", filename="paper_summary.md")


@app.post("/api/compare")
def compare(request: CompareRequest) -> dict[str, object]:
    try:
        scenario = get_scenario(request.scenario_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    without_trace = save_trace(run_investigation(scenario, []))
    retrieved = retrieve_skills_for_scenario(scenario)
    with_trace = save_trace(run_investigation(scenario, retrieved))
    improved = (not without_trace.matched_expected) and with_trace.matched_expected
    confidence_delta = round(with_trace.final_answer.confidence - without_trace.final_answer.confidence, 2)
    comparison = {
        "improved": improved,
        "confidence_delta": confidence_delta,
        "summary": (
            "The saved skill helped the investigator prioritize reusable debugging procedure over the obvious symptom."
            if improved
            else "No clear improvement was detected; the skill library may not contain a relevant approved skill yet."
        ),
        "expected_answer": scenario.expected_answer,
        "skills_used": [skill.name for skill in retrieved],
    }
    return {
        "scenario_id": scenario.scenario_id,
        "without_skill": without_trace.model_dump(),
        "with_skill": with_trace.model_dump(),
        "agent_logs": [log.model_dump() for log in without_trace.agent_logs + with_trace.agent_logs],
        "comparison": comparison,
    }
