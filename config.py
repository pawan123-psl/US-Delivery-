

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

#LLM 
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
LLM_TEMPERATURE: float = 0.0          # deterministic output
LLM_MAX_TOKENS: int = 1024

#RAG 
TOP_K_DOCS: int = 3                   

# Data paths 
_BASE = Path(__file__).parent
DATA_DIR: Path = Path(os.getenv("DATA_DIR", str(_BASE / ".." / "Task" / "resources" / "starter-repo")))
TICKETS_PATH: Path = DATA_DIR / "data" / "tickets.json"
ACCOUNTS_PATH: Path = DATA_DIR / "data" / "accounts.json"
KB_DIR: Path = DATA_DIR / "knowledge-base"

#  Prompt versioning 
PROMPT_VERSION: str = "v1.0"
