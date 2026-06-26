#!/usr/bin/env python3
"""Create or refresh trace_context.json for a workspace session."""

import argparse
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone, timedelta

HARNESS_ROOT = os.path.normpath("/Users/huron/code/ai_lab/biogpu-harness")
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))

try:
    import yaml
except ImportError:
    print(json.dumps({"status": "error", "errors": ["PyYAML not installed"]}))
    sys.exit(2)


def now_iso():
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz).isoformat(timespec="seconds")


def short_id():
    return uuid.uuid4().hex[:6]


def ts_compact():
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz).strftime("%Y%m%d_%H%M%S")


def check_workspace(workspace):
    ws = os.path.normpath(workspace)
    if ws == HARNESS_ROOT:
        return "workspace must not be HARNESS_ROOT"
    if ws.startswith(HARNESS_ROOT + os.sep):
        return "workspace must not be inside HARNESS_ROOT"
    return None


def run_validator(script, workspace):
    r = subprocess.run(
        [sys.executable, os.path.join(SCRIPTS_DIR, script), "--workspace", workspace],
        capture_output=True, text=True,
    )
    return r.returncode, r.stdout.strip()


def load_context(workspace):
    ctx = {}
    try:
        with open(os.path.join(workspace, "biogpu_project.yaml")) as f:
            proj = yaml.safe_load(f)
        ctx["tool_name"] = proj.get("tool_name")
    except Exception:
        ctx["tool_name"] = None

    try:
        with open(os.path.join(workspace, "state", "task_state.json")) as f:
            state = json.load(f)
        ctx["task_id"] = state.get("task_id")
    except Exception:
        ctx["task_id"] = None

    return ctx


def main():
    parser = argparse.ArgumentParser(description="Initialize trace context for a workspace")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--created-by", dest="created_by", default="bio-gpu-team")
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    ws_err = check_workspace(args.workspace)
    if ws_err:
        print(json.dumps({"status": "fail", "errors": [ws_err]}))
        sys.exit(1)

    errors = []
    for script in ("validate_biogpu_project.py", "validate_task_state.py"):
        rc, out = run_validator(script, args.workspace)
        if rc != 0:
            try:
                errs = json.loads(out).get("errors", [])
                errors.extend(errs)
            except Exception:
                errors.append(f"{script} failed (exit {rc})")

    if errors:
        print(json.dumps({"status": "fail", "errors": errors}))
        sys.exit(1)

    ctx = load_context(args.workspace)
    ts = ts_compact()
    sid = short_id()
    tool_slug = (ctx.get("tool_name") or "unknown").replace("-", "_")

    session_id = f"sess_{ts}_{sid}"
    trace_id = f"trace_{tool_slug}_{ts}_{sid}"
    agent_slug = args.created_by.replace("-", "_").replace("/", "_")
    span_id = f"span_{agent_slug}_{ts}_{sid}"
    now = now_iso()

    trace_ctx = {
        "task_id": ctx.get("task_id"),
        "tool_name": ctx.get("tool_name"),
        "session_id": session_id,
        "trace_id": trace_id,
        "root_span_id": span_id,
        "current_span_id": span_id,
        "created_at": now,
        "created_by": args.created_by,
        "updated_at": now,
        "notes": args.notes,
    }

    state_dir = os.path.join(args.workspace, "state")
    os.makedirs(state_dir, exist_ok=True)
    out_path = os.path.join(state_dir, "trace_context.json")
    with open(out_path, "w") as f:
        json.dump(trace_ctx, f, indent=2)

    print(json.dumps({"status": "pass", "trace_context_path": out_path, "trace_context": trace_ctx}, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
