#!/usr/bin/env bash

set -euo pipefail

if ! command -v node >/dev/null 2>&1; then
    echo "Error: Linux Node.js is not installed in WSL." >&2
    echo "Install Node.js inside WSL (for example with nvm), then run this script again." >&2
    exit 1
fi

case "$(command -v npm 2>/dev/null || true)" in
    /mnt/*)
        echo "Error: Windows npm is being used from WSL." >&2
        echo "Install Node.js inside WSL so that 'node' and 'npm' resolve to Linux binaries." >&2
        exit 1
        ;;
esac

python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest test_mcp_server.py -v
npm install
npm run inspector
