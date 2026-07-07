# LogLearner

Every attempt teaches the next one.

LogLearner is a small-data agent-learning prototype. It shows how an agent can turn a short debugging attempt into a reusable skill, save that skill, and use it to improve on a related task.

The project intentionally avoids becoming a full observability platform. The logs are small curated scenarios; the core product is the learning loop:

```text
Attempt -> Reflect -> Learn Skill -> Reuse
```

## What It Demonstrates

- An Investigator Agent solves a debugging-style micro-scenario.
- A trace is stored with summarized steps, not hidden chain-of-thought.
- A Reflection Agent extracts one reusable lesson.
- A Verifier Agent approves, revises, or rejects the proposed skill.
- Approved skills are saved in a local JSON skill library.
- A paired scenario can be run with and without skills to show improvement.

## Agents

- Investigator Agent: runs keyword and timeline tools, retrieves skills when requested, and produces a structured answer with evidence and confidence.
- Reflection Agent: reviews the trace and proposes one reusable skill.
- Verifier Agent: checks that a skill is useful, general, non-duplicative, and free of secret-like data.

This prototype uses deterministic agent logic so the demo works without API keys. The code is structured so real LLM calls can be swapped in later for answer generation, reflection, and verification.

## Scenarios

The scenario library contains four learn/test pairs:

- Loudest Error Trap
- Deployment Suspicion
- Retry Storm
- Missing Evidence

Each scenario includes a prompt, short log snippet, expected answer, common mistake, and target skill.

## Safety

- Inputs are passed through a redaction tool before trace storage.
- Traces store summarized reasoning only.
- Verifier rejects duplicate and secret-like skills.
- No API keys are required or committed.

## Run Locally

Backend:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

## Demo Flow

1. Select `Database Connection Exhaustion`.
2. Click `Run`.
3. Click `Reflect`.
4. Click `Verify`.
5. Click `Save`.
6. Click `Compare`.

The comparison runs the paired Redis scenario without and with the saved `Avoid the Loudest Error Trap` skill.

## API

- `GET /api/scenarios`
- `POST /api/attempt`
- `POST /api/reflect`
- `POST /api/verify-skill`
- `POST /api/save-skill`
- `GET /api/skills`
- `POST /api/compare`
- `GET /api/experiments/config`
- `POST /api/experiments/run`
- `GET /api/experiments/latest`
- `GET /api/experiments/export/csv`
- `GET /api/experiments/export/summary`

## Research Mode

LogLearner includes a small experiment runner for turning the demo into a research-paper-style prototype study.

Hypothesis:

```text
Agents that reflect on their own debugging traces and store verified reusable skills will solve related debugging tasks more accurately than agents without saved skills.
```

The experiment runner supports:

- Baseline: solve test scenarios with no saved skills.
- Learning: run paired learn scenarios, reflect, verify, and save skills.
- Reuse: solve paired test scenarios with learned skill retrieval enabled.
- Random skill control: solve test scenarios with an unrelated skill.
- Ablations: verifier on/off, reflection on/off, retrieval on/off, duplicate filtering on/off, random control on/off.

Run experiments from the frontend `Research Mode` panel, or call:

```bash
curl -X POST http://127.0.0.1:8000/api/experiments/run \
  -H "Content-Type: application/json" \
  -d '{"verifier_enabled":true,"reflection_enabled":true,"skill_retrieval_enabled":true,"duplicate_filtering_enabled":true,"random_skill_control_enabled":true,"persist_experiment_skills_to_main_library":false}'
```

Exports are written to:

- `backend/data/experiment_runs.json`: full structured experiment history.
- `backend/data/experiment_results.csv`: row-level condition results.
- `backend/data/paper_summary.md`: Markdown paper summary with method, metrics, table, examples, limitations, and future work.

Interpret results cautiously:

- Accuracy compares whether answers match curated expected answers.
- Confidence is the Investigator's reported confidence, not a calibrated probability.
- Evidence quality is a lightweight proxy based on cited evidence count.
- Improvement rate counts paired cases where baseline was wrong and reuse was correct.
- Random skill control helps check whether improvement comes from relevant learned skills rather than generic prompting.

Limitations:

- The benchmark is small and curated.
- Results show feasibility, not broad statistical generalization.
- More held-out scenarios, human labels, and stronger baselines are needed for a publishable empirical claim.
- User-uploaded project context should be treated as private and should not be copied into public paper artifacts without review.

## Out of Scope

LogLearner is not a Datadog/New Relic replacement, a production incident workflow, a real-time monitor, a vector database demo, or a large-scale memory benchmark. It is a focused hackathon prototype for visible small-data agent learning.
