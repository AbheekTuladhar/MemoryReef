"""Runtime configuration for MemoryReef.

Loads the git-ignored repo-root ``.env`` (so GOOGLE_* credentials are available
to the Google ADK / Gemini backend) and exposes the model id. Backend selection
(AI Studio vs Vertex) is env-only and handled by google-genai itself; we never
read or print secret values here.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Repo root is two levels up from this file (backend/config.py -> repo/).
_REPO_ROOT = Path(__file__).resolve().parents[1]

# Load .env once at import time; do not override already-exported env vars.
load_dotenv(_REPO_ROOT / ".env", override=False)

# Gemini model id, overridable via env. Flash keeps the demo fast and cheap.
MODEL = os.getenv("MEMORYREEF_MODEL", "gemini-2.5-flash")
