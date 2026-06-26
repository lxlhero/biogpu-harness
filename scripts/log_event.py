#!/usr/bin/env python3
"""Append a structured event to <workspace>/logs/events.jsonl."""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta

HARNESS_ROOT = os.path.normpath("/Users/huron/code/ai_lab/biogpu-harness")

VALID_EVENT_TYPES = {
    "project_initialized", "source_setup_completed", "benchmark_designed",
    "profiling_completed", "feasibility_completed", "test_plan_created",
    "test_started", "test_completed", "test_failed",
    "implementation_started", "implementation_completed", "review_completed",
    "module_test_completed", "failure_diagnosed", "execution_plan_created",
    "final_report_written", "blocked", "manual_approval_required", "dry_run_completed",
}

VALID_STATUSES = {"pass", "fail", "running", "blocked", "warning", "info"}

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))


def now_iso():
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz).isoformat(timespec="seconds")


def check_workspace(workspace):
    ws = os.path.normpath(workspace)
    if ws == HARNESS_ROOT:
        return "workspace must not be HARNESS_ROOT"
    if ws.startswith(HARNESS_ROOT + os.sep):
        return "workspace must not be inside HARNESS_ROOT"
    return None


def run_validator(script, workspace):
    result = subprocess.run(
        [sys.executable, os.path.join(SCRIPTS_DIR, script), "--workspace", workspace],
        capture_output=True, text=True,
    )
    return result.returncode, result.stdout.strip()


def load_context(workspace):
    ctx = {}
    project_file = os.path.join(workspace, "biogpu_project.yaml")
    state_file = os.path.join(workspace, "state", "task_state.json")

    try:
        import yaml
        with open(project_file) as f:
            proj = yaml.safe_load(f)
        ctx["tool_name"] = proj.get("tool_name")
    except Exception:
        ctx["tool_name"] = None

    try:
        with open(state_file) as f:
            state = json.load(f)
        ctx["task_id"] = state.get("task_id")
        ctx["mode"] = state.get("mode")
        ctx["current_step"] = state.get("current_step")
        ctx["next_action"] = state.get("next_action")
        ctx["attempt"] = state.get("attempt")
    except Exception:
        ctx.setdefault("task_id", None)
        ctx.setdefault("mode", None)
        ctx.setdefault("current_step", None)
        ctx.setdefault("next_action", None)
        ctx.setdefault("attempt", None)

    return ctx


def build_event(args_ns, ctx):
    return {
        "timestamp": now_iso(),
        "tool_name": ctx.get("tool_name"),
        "task_id": ctx.get("task_id"),
        "mode": ctx.get("mode"),
        "agent": args_ns.agent,
        "event_type": args_ns.event_type,
        "status": args_ns.status,
        "step": args_ns.step,
        "module": args_ns.module,
        "attempt": ctx.get("attempt"),
        "artifact_path": args_ns.artifact_path,
        "next_action": ctx.get("next_action"),
        "message": args_ns.message,
    }


def main():
    parser = argparse.ArgumentParser(description="Append event to workspace logs/events.jsonl")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--agent", default=None)
    parser.add_argument("--event-type", dest="event_type", default=None)
    parser.add_argument("--status", default=None)
    parser.add_argument("--step", default=None)
    parser.add_argument("--module", default=None)
    parser.add_argument("--artifact-path", dest="artifact_path", default=None)
    parser.add_argument("--message", default=None)
    parser.add_argument("--event-json", dest="event_json", default=None,
                        help="Path to a JSON file containing event fields (merged over CLI args)")
    args = parser.parse_args()

    errors = []
    warnings = []

    # workspace safety check
    ws_err = check_workspace(args.workspace)
    if ws_err:
        out = {"status": "fail", "errors": [{"field": "workspace", "message": ws_err}], "warnings": []}
        print(json.dumps(out, indent=2))
        sys.exit(1)

    # run validators
    for script in ("validate_biogpu_project.py", "validate_task_state.py"):
        rc, output = run_validator(script, args.workspace)
        if rc != 0:
            try:
                result = json.loads(output)
                for e in result.get("errors", []):
                    errors.append({"field": script, "message": e})
            except Exception:
                errors.append({"field": script, "message": f"validator failed (exit {rc})"})

    if errors:
        out = {"status": "fail", "errors": errors, "warnings": warnings}
        print(json.dumps(out, indent=2))
        sys.exit(1)

    # load event from --event-json if provided
    extra = {}
    if args.event_json:
        try:
            with open(args.event_json) as f:
                extra = json.load(f)
        except Exception as e:
            out = {"status": "fail", "errors": [{"field": "event_json", "message": str(e)}], "warnings": []}
            print(json.dumps(out, indent=2))
            sys.exit(2)

    # merge: CLI args win over event_json defaults
    for field in ("agent", "event_type", "status", "step", "module", "artifact_path", "message"):
        cli_val = getattr(args, field.replace("-", "_"), None)
        if cli_val is None and field in extra:
            setattr(args, field.replace("-", "_"), extra[field])

    event_type = getattr(args, "event_type", None)
    status = args.status

    if not event_type:
        out = {"status": "fail", "errors": [{"field": "event_type", "message": "--event-type is required"}], "warnings": []}
        print(json.dumps(out, indent=2))
        sys.exit(1)

    if event_type not in VALID_EVENT_TYPES:
        out = {"status": "fail", "errors": [{"field": "event_type", "message": f"unknown event_type: {event_type!r}; valid: {sorted(VALID_EVENT_TYPES)}"}], "warnings": []}
        print(json.dumps(out, indent=2))
        sys.exit(1)

    if status and status not in VALID_STATUSES:
        out = {"status": "fail", "errors": [{"field": "status", "message": f"unknown status: {status!r}; valid: {sorted(VALID_STATUSES)}"}], "warnings": []}
        print(json.dumps(out, indent=2))
        sys.exit(1)

    # load context from workspace
    ctx = load_context(args.workspace)
    if ctx.get("tool_name") is None:
        warnings.append("could not read tool_name from biogpu_project.yaml")

    event = build_event(args, ctx)

    # write
    logs_dir = os.path.join(args.workspace, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    event_file = os.path.join(logs_dir, "events.jsonl")

    line = json.dumps(event, ensure_ascii=False)
    with open(event_file, "a") as f:
        f.write(line + "\n")

    out = {
        "status": "pass",
        "event_file": event_file,
        "event_type": event_type,
        "errors": [],
        "warnings": warnings,
    }
    print(json.dumps(out, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
