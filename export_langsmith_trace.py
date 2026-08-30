#!/usr/bin/env python3
"""Export a compact LangSmith run fragment as JSON."""

from __future__ import annotations

import argparse
import json
import os
import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_ENV_FILE = PROJECT_DIR / ".env"
DEFAULT_OUTPUT = PROJECT_DIR / "langsmith_trace_fragment.json"


def json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def compact_run(run: Any, include_children: bool = True) -> dict[str, Any]:
    data = run.model_dump() if hasattr(run, "model_dump") else run.dict()
    fragment = {
        "id": data.get("id"),
        "trace_id": data.get("trace_id"),
        "parent_run_id": data.get("parent_run_id"),
        "name": data.get("name"),
        "run_type": data.get("run_type"),
        "project_name": data.get("session_name") or data.get("project_name"),
        "start_time": data.get("start_time"),
        "end_time": data.get("end_time"),
        "inputs": data.get("inputs"),
        "outputs": data.get("outputs"),
        "error": data.get("error"),
        "tags": data.get("tags"),
        "metadata": (data.get("extra") or {}).get("metadata"),
        "url_hint": "Open the run in LangSmith UI by searching for this id or trace_id.",
    }

    child_runs = data.get("child_runs") or []
    if include_children and child_runs:
        fragment["child_runs"] = [
            compact_run(child, include_children=False) for child in child_runs
        ]

    return fragment


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export latest or selected LangSmith run as a JSON fragment."
    )
    parser.add_argument("--run-id", help="Specific LangSmith run id to export.")
    parser.add_argument(
        "--project",
        help="Optional override for LANGSMITH_PROJECT from .env.",
    )
    parser.add_argument(
        "--name",
        help="Optional run name filter when selecting the latest root run.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help=f"Output JSON path. Default: {DEFAULT_OUTPUT}",
    )
    parser.add_argument(
        "--no-children",
        action="store_true",
        help="Do not include immediate child runs for --run-id exports.",
    )
    return parser.parse_args()


def main() -> int:
    warnings.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        message=r"list_runs\(\) is deprecated.*",
    )
    load_dotenv(DEFAULT_ENV_FILE)
    args = parse_args()

    if not os.getenv("LANGSMITH_API_KEY"):
        print(f"Missing LANGSMITH_API_KEY. Add it to {DEFAULT_ENV_FILE}", file=sys.stderr)
        return 2

    project_name = args.project or os.getenv("LANGSMITH_PROJECT")
    if not project_name and not args.run_id:
        print(
            f"Missing LANGSMITH_PROJECT. Add it to {DEFAULT_ENV_FILE} "
            "or pass --run-id for a specific run.",
            file=sys.stderr,
        )
        return 2

    try:
        from langsmith import Client
        from langsmith import utils as langsmith_utils
    except ImportError:
        print(
            "Missing langsmith package. Run: "
            "source .venv/bin/activate && python -m pip install -r requirements.txt",
            file=sys.stderr,
        )
        return 2

    client = Client()

    if args.run_id:
        run = client.read_run(args.run_id, load_child_runs=not args.no_children)
    else:
        try:
            runs = client.list_runs(project_name=project_name, is_root=True, limit=50)
            run = next((item for item in runs if not args.name or item.name == args.name), None)
        except langsmith_utils.LangSmithNotFoundError:
            projects = [project.name for project in client.list_projects(limit=20)]
            print(f"LangSmith project {project_name!r} was not found.", file=sys.stderr)
            if projects:
                print("Available projects:", file=sys.stderr)
                for available_project in projects:
                    print(f"  - {available_project}", file=sys.stderr)
            print(f"Set LANGSMITH_PROJECT in {DEFAULT_ENV_FILE}", file=sys.stderr)
            return 1

        if run is None:
            print(
                f"No root runs found in LangSmith project {project_name!r}. "
                "Run the traced demo first or pass --run-id.",
                file=sys.stderr,
            )
            return 1

        if not args.no_children:
            run = client.read_run(run.id, load_child_runs=True)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fragment = compact_run(run, include_children=not args.no_children)
    output_path.write_text(
        json.dumps(fragment, ensure_ascii=False, indent=2, default=json_default) + "\n",
        encoding="utf-8",
    )

    print(f"Wrote {output_path}")
    print(f"run_id={fragment.get('id')}")
    print(f"trace_id={fragment.get('trace_id')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
