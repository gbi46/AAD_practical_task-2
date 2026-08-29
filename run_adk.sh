#!/usr/bin/env bash

set -euo pipefail

if ! command -v python3.12 >/dev/null 2>&1; then
    echo "Error: Python 3.12 is not installed." >&2
    echo "Install it with uv: uv python install 3.12" >&2
    exit 1
fi

if [[ ! -x .venv/bin/python ]] || [[ "$(.venv/bin/python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')" != "3.12" ]]; then
    echo "Creating a Python 3.12 virtual environment in .venv..."
    python3.12 -m venv --clear .venv
fi

.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python adk_agent.py
