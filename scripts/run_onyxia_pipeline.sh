#!/usr/bin/env bash
set -euo pipefail

if [ -z "${ESG_PROJECT_ROOT:-}" ]; then
  export ESG_PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi

export PYTHONIOENCODING="${PYTHONIOENCODING:-utf-8}"
export PYTHONUNBUFFERED="${PYTHONUNBUFFERED:-1}"

cd "$ESG_PROJECT_ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-.venv}"

if [ ! -d "$VENV_DIR" ]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip
python -m pip install -r requirements_all.txt

PROFILE="${PROFILE:-onyxia_pilot_5x2}"
RUN_ID="${RUN_ID:-}"

cd "$ESG_PROJECT_ROOT/ESGOrchestrator"

COMMAND=(python scripts/run_pipeline.py --profile "$PROFILE")
if [ -n "$RUN_ID" ]; then
  COMMAND+=(--run-id "$RUN_ID")
fi
if [ "${DRY_RUN:-0}" = "1" ]; then
  COMMAND+=(--dry-run)
fi

echo "ESG_PROJECT_ROOT=$ESG_PROJECT_ROOT"
echo "Running profile: $PROFILE"
echo "${COMMAND[@]}"
"${COMMAND[@]}"
