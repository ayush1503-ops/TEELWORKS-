"""Central settings for the Onion Quality Analyzer backend."""
from pathlib import Path

# --- Project paths ---
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent   # .../backend
PROJECT_ROOT = BACKEND_DIR.parent                             # .../onion-grader
FRONTEND_DIR = PROJECT_ROOT / "frontend"
CONFIG_DIR = PROJECT_ROOT / "config"
GRADING_RULES_PATH = CONFIG_DIR / "grading_rules.yaml"
DATA_DIR = BACKEND_DIR / "data"          # SQLite DB lives here (created on demand)

# --- Upload limits (security) ---
MAX_UPLOAD_BYTES = 8 * 1024 * 1024        # 8 MB
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}

# --- Batch analysis limits ---
MAX_BATCH_FILES = 25                      # per /api/batch request

# --- Rate limiting ---
RATE_LIMIT_REQUESTS = 30
RATE_LIMIT_WINDOW_SECONDS = 60

# --- App metadata ---
APP_NAME = "Onion Quality Analyzer"
APP_VERSION = "0.2.0"
CURRENT_PHASE = 14          # full prototype built; ML training awaits dataset (Phase 4/5)
