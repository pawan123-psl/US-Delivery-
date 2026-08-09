"""
config.py
─────────
Centralised configuration loaded from environment variables.
All tuneable values live here — no magic strings scattered across modules.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Don't override env vars already set in CI/production environments
load_dotenv(override=False)

# ── LLM ──────────────────────────────────────────────────────────────────────
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
LLM_TEMPERATURE: float = 0.0      # deterministic output
LLM_MAX_TOKENS: int = 1024

# ── RAG ──────────────────────────────────────────────────────────────────────
TOP_K_DOCS: int = 3               # KB chunks to retrieve per query

# ── Data paths ────────────────────────────────────────────────────────────────
# Resolution order:
#   1. DATA_DIR env var (explicit override — used in CI and custom setups)
#   2. ./data/  — bundled data folder committed to the repo (works after git clone)
#   3. ../Task/resources/starter-repo — original dev-machine layout (fallback)

_BASE = Path(__file__).parent

def _resolve_data_dir() -> Path:
    # Explicit env var always wins
    env_val = os.getenv("DATA_DIR", "")
    if env_val:
        return Path(env_val)
    # Bundled data folder inside the repo (present after git clone)
    bundled = _BASE / "data"
    if bundled.exists():
        return bundled
    # Original dev layout fallback
    return _BASE / ".." / "Task" / "resources" / "starter-repo"

DATA_DIR: Path = _resolve_data_dir()
TICKETS_PATH: Path = DATA_DIR / "data" / "tickets.json"
ACCOUNTS_PATH: Path = DATA_DIR / "data" / "accounts.json"
KB_DIR: Path = DATA_DIR / "knowledge-base"

# ── Prompt versioning ─────────────────────────────────────────────────────────
PROMPT_VERSION: str = "v1.0"
