#!/usr/bin/env python3
"""Append a structured event to <workspace>/logs/events.jsonl."""

import argparse
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.schema_utils import load_schema, validate_against_schema

HARNESS_ROOT = os.path.normpath("/Users/huron/code/ai_lab/biogpu-harness")

VALID_EVENT_TYPES = {
    "project_initialized", "source_setup_completed", "benchmark_designed",
    "profiling_completed", "feasibility_completed", "test_plan_created",
    "test_started", "test_completed", "test_failed",
    "implementation_started", "implementation_completed", "review_completed",
    "module_test_completed", "failure_diagnosed", "execution_plan_created",
    "final_report_written", "blocked", "manual_approval_required", "dry_run_completed",
    # Phase 2.2-A additions
    "trace_context_created", "decision_made", "command_executed",
    "artifact_created", "artifact_updated", "state_updated",
    "gate_checked", "trace_analysis_requested",
}

VALID_STATUSES = {"pass", "fail", "running", "blocked", "warning", "info"}

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))


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
    result = subprocess.run(
        [sys.executable, os.path.join(SCRIPTS_DIR, script), "--workspace", workspace],
        capture_output=True, text=True,
    )
    return result.returncode, result.stdout.strip()


def load_project_context(workspace):
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


def load_trace_context(workspace):
    path = os.path.join(workspace, "state", "trace_context.json")
    if not os.path.isfile(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def make_artifact_id(artifact_path, explicit_id=None):
    if explicit_id:
        return explicit_id
    if not artifact_path:
        return None
    # derive from filename: reports/test_results/foo.json → art_foo_json_<short>
    base = os.path.basename(artifact_path).replace(".", "_")
    return f"art_{base}_{short_id()}"


def build_event(args_ns, proj_ctx, trace_ctx):
    ts = ts_compact()
    sid = short_id()
    event_id = f"evt_{ts}_{sid}"

    # resolve tracing fields: explicit CLI > trace_context.json > None
    trace_id = args_ns.trace_id or (trace_ctx.get("trace_id") if trace_ctx else None)
    session_id = args_ns.session_id or (trace_ctx.get("session_id") if trace_ctx else None)
    span_id = args_ns.span_id or (trace_ctx.get("current_span_id") if trace_ctx else None)
    parent_span_id = args_ns.parent_span_id or (trace_ctx.get("root_span_id") if trace_ctx else None)

    artifact_id = make_artifact_id(args_ns.artifact_path, args_ns.artifact_id)

    return {
        "event_id": event_id,
        "timestamp": now_iso(),
        "tool_name": proj_ctx.get("tool_name"),
        "task_id": proj_ctx.get("task_id"),
        "session_id": session_id,
        "trace_id": trace_id,
        "span_id": span_id,
        "parent_span_id": parent_span_id,
        "mode": proj_ctx.get("mode"),
        "agent": args_ns.agent,
        "event_type": args_ns.event_type,
        "status": args_ns.status,
        "step": args_ns.step,
        "module": args_ns.module,
        "attempt": proj_ctx.get("attempt"),
        "decision_id": args_ns.decision_id,
        "command_id": args_ns.command_id,
        "artifact_id": artifact_id,
        "artifact_path": args_ns.artifact_path,
        "command": args_ns.command,
        "exit_code": args_ns.exit_code,
        "next_action": proj_ctx.get("next_action"),
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
    parser.add_argument("--event-json", dest="event_json", default=None)
    # tracing fields
    parser.add_argument("--trace-id", dest="trace_id", default=None)
    parser.add_argument("--session-id", dest="session_id", default=None)
    parser.add_argument("--span-id", dest="span_id", default=None)
    parser.add_argument("--parent-span-id", dest="parent_span_id", default=None)
    parser.add_argument("--decision-id", dest="decision_id", default=None)
    parser.add_argument("--command-id", dest="command_id", default=None)
    parser.add_argument("--artifact-id", dest="artifact_id", default=None)
    parser.add_argument("--command", dest="command", default=None)
    parser.add_argument("--exit-code", dest="exit_code", type=int, default=None)
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

    # require trace_context.json (unless all tracing fields provided explicitly)
    trace_ctx = load_trace_context(args.workspace)
    has_explicit_trace = args.trace_id and args.session_id and args.span_id
    if trace_ctx is None and not has_explicit_trace:
        out = {
            "status": "fail",
            "errors": [{"field": "trace_context", "message": (
                "trace_context.json not found. "
                "Run: python scripts/init_trace_context.py --workspace <workspace> first."
            )}],
            "warnings": [],
        }
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

    # merge CLI args over event_json defaults
    for field in ("agent", "event_type", "status", "step", "module", "artifact_path", "message",
                  "trace_id", "session_id", "span_id", "parent_span_id",
                  "decision_id", "command_id", "artifact_id", "command"):
        cli_val = getattr(args, field, None)
        if cli_val is None and field in extra:
            setattr(args, field, extra[field])

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

    proj_ctx = load_project_context(args.workspace)
    if proj_ctx.get("tool_name") is None:
        warnings.append("could not read tool_name from biogpu_project.yaml")

    event = build_event(args, proj_ctx, trace_ctx)

    # ── schema validation before writing ─────────────────────────────────────
    try:
        schema = load_schema("event.schema.json")
        schema_errs = validate_against_schema(event, schema)
    except Exception as e:
        schema_errs = [{"path": "(schema)", "message": str(e)}]

    if schema_errs:
        out = {
            "status": "fail",
            "schema_errors": schema_errs,
            "errors": [e["message"] for e in schema_errs],
            "warnings": warnings,
        }
        print(json.dumps(out, indent=2))
        sys.exit(1)

    logs_dir = os.path.join(args.workspace, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    event_file = os.path.join(logs_dir, "events.jsonl")

    with open(event_file, "a") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

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
