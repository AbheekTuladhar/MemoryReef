"""API-level end-to-end test for the MemoryReef agent learning loop.

This single happy-path test walks the whole story and asserts the core claim:
reusing a learned skill improves the answer.

Loop exercised against the FastAPI app via TestClient:
  1. /api/attempt (use_skills=false) on the TEST scenario -> Dory falls for the
     "loudest error" and gives a WRONG, low-confidence answer.
  2. /api/reflect on that trace          -> Nemo proposes a reusable skill.
  3. /api/verify-skill on that skill     -> Puffer APPROVES it.
  4. /api/save-skill                     -> the skill is persisted.
  5. /api/compare on the same scenario   -> with-skill beats without-skill
     (improved is true, confidence_delta > 0).

Test isolation
--------------
All stores (skills/traces/scenarios) read and write JSON files under
``backend/data`` via ``backend.tools.json_store.DATA_DIR``, which is read at
call time by ``read_json`` / ``write_json``. We therefore monkeypatch that
module global to a fresh temp directory (fixture below), seeding only the
curated ``scenarios.json`` and starting with an EMPTY skills/traces library.
The real data files are never opened, so the test is fully repeatable with no
side effects.

Run this test:
    cd /home/raj/work/MemoryReef
    uv run pytest backend/tests/test_e2e_loop.py -v
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import backend.tools.json_store as json_store
from backend.main import app

# The one scenario we drive the whole loop on. It is the "test" half of the
# loudest_error pair: a naive agent blames the repeated `frontend ERROR 503`
# (the loudest error) instead of the real cause, Redis memory exhaustion.
# (Learn scenarios are seeded to answer correctly even without skills, so the
# genuine wrong answer only happens on a test scenario.)
SCENARIO_ID = "loudest_error_1b"
EXPECTED = "Redis memory exhaustion"
REAL_DATA_DIR = Path(json_store.__file__).resolve().parents[1] / "data"


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Point the JSON stores at an isolated temp data dir seeded with scenarios."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    # Seed the curated scenarios so get_scenario / retrieval work.
    shutil.copy(REAL_DATA_DIR / "scenarios.json", data_dir / "scenarios.json")
    # Start with an empty skill library and trace log for a deterministic story.
    (data_dir / "skills.json").write_text("[]\n", encoding="utf-8")
    (data_dir / "traces.json").write_text("[]\n", encoding="utf-8")
    # read_json/write_json read this global at call time, so patching it isolates
    # every store the endpoints use.
    monkeypatch.setattr(json_store, "DATA_DIR", data_dir)
    return TestClient(app)


def test_reusing_a_learned_skill_improves_the_answer(client: TestClient) -> None:
    # --- Step 1: attempt WITHOUT skills -> wrong, low-confidence answer ---------
    resp = client.post("/api/attempt", json={"scenario_id": SCENARIO_ID, "use_skills": False})
    assert resp.status_code == 200
    attempt = resp.json()
    assert attempt["trace"]["matched_expected"] is False  # fell for the loudest error
    assert attempt["answer"]["confidence"] < 0.7  # and it wasn't confident
    trace_id = attempt["trace"]["trace_id"]

    # --- Step 2: reflect on that failed trace -> a proposed skill ---------------
    resp = client.post("/api/reflect", json={"trace_id": trace_id})
    assert resp.status_code == 200
    proposed_skill = resp.json()["proposed_skill"]
    # For the loudest_error pair the reflection proposes this named lesson.
    assert "loudest" in proposed_skill["name"].lower()

    # --- Step 3: verify the skill -> Puffer approves ---------------------------
    resp = client.post("/api/verify-skill", json={"skill": proposed_skill})
    assert resp.status_code == 200
    verification = resp.json()
    assert verification["status"] == "approved"
    approved_skill = verification["final_skill"]

    # --- Step 4: save the skill -> persisted as approved -----------------------
    resp = client.post("/api/save-skill", json={"skill": approved_skill})
    assert resp.status_code == 200
    assert resp.json()["skill"]["status"] == "approved"
    # It is now retrievable from the (isolated) library.
    assert any(s["name"] == approved_skill["name"] for s in client.get("/api/skills").json()["skills"])

    # --- Step 5: compare -> with-skill beats without-skill ---------------------
    resp = client.post("/api/compare", json={"scenario_id": SCENARIO_ID})
    assert resp.status_code == 200
    comparison = resp.json()["comparison"]
    assert comparison["improved"] is True  # the learned skill fixed the answer
    assert comparison["confidence_delta"] > 0  # and raised confidence
