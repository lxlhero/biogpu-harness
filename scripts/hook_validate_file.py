#!/usr/bin/env python3
"""
PostToolUse hook: validate a modified file against BioGPU-Harness rules.

Two modes:
  --file <path>   direct file path (CLI / smoke test)
  --stdin         read hook JSON from stdin and extract tool_input.file_path
"""

import argparse
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.schema_utils import load_schema, validate_against_schema, load_yaml_or_json

HARNESS_ROOT = os.path.normpath("/Users/huron/code/ai_lab/biogpu-harness")
PYTHON = sys.executable
SCRIPTS = os.path.dirname(os.path.abspath(__file__))


# ── workspace detection ───────────────────────────────────────────────────────

def _detect_workspace(filepath):
    """Walk up from filepath to find the workspace root."""
    p = os.path.normpath(filepath)
    parts = p.split(os.sep)
    for i in range(len(parts) - 1, 0, -1):
        candidate = os.sep.join(parts[:i])
        if os.path.isfile(os.path.join(candidate, "biogpu_project.yaml")):
            return candidate
    return None


def _result(status, filepath, checks, errors, warnings):
    out = {"status": status, "file": filepath, "checks": checks, "errors": errors, "warnings": warnings}
    print(json.dumps(out, indent=2))
    # For PostToolUse: if fail, feed back to Claude as context
    if status == "fail":
        reason = "; ".join(
            e.get("message", str(e)) if isinstance(e, dict) else str(e)
            for e in errors
        )
        hook_out = {"decision": "block", "reason": f"[BioGPU hook] {os.path.basename(filepath)}: {reason}"}
        print(json.dumps(hook_out), file=sys.stderr)
    return status


# ── file-type handlers ────────────────────────────────────────────────────────

def check_biogpu_project(filepath, workspace):
    r = subprocess.run(
        [PYTHON, os.path.join(SCRIPTS, "validate_biogpu_project.py"), "--workspace", workspace],
        capture_output=True, text=True,
    )
    try:
        data = json.loads(r.stdout)
    except Exception:
        data = {}
    errors = data.get("errors", [])
    if errors:
        return _result("fail", filepath, ["validate_biogpu_project"], [{"message": e} for e in errors], [])
    return _result("pass", filepath, ["validate_biogpu_project"], [], [])


def check_task_state(filepath, workspace):
    r = subprocess.run(
        [PYTHON, os.path.join(SCRIPTS, "validate_task_state.py"), "--workspace", workspace],
        capture_output=True, text=True,
    )
    try:
        data = json.loads(r.stdout)
    except Exception:
        data = {}
    errors = data.get("errors", [])
    if errors:
        return _result("fail", filepath, ["validate_task_state"], [{"message": e} for e in errors], [])
    return _result("pass", filepath, ["validate_task_state"], [], [])


def check_trace_context(filepath):
    try:
        data = load_yaml_or_json(filepath)
        schema = load_schema("trace_context.schema.json")
        schema_errs = validate_against_schema(data, schema)
    except Exception as e:
        return _result("fail", filepath, ["trace_context_schema"], [{"message": str(e)}], [])
    if schema_errs:
        return _result("fail", filepath, ["trace_context_schema"], schema_errs, [])
    return _result("pass", filepath, ["trace_context_schema"], [], [])


def check_events_jsonl(filepath):
    """Validate the last line of events.jsonl against event.schema.json."""
    try:
        last_line = None
        with open(filepath) as f:
            for line in f:
                line = line.strip()
                if line:
                    last_line = line
        if not last_line:
            return _result("pass", filepath, ["event_schema_last_line"], [], ["events.jsonl is empty"])
        event = json.loads(last_line)
        schema = load_schema("event.schema.json")
        schema_errs = validate_against_schema(event, schema)
    except Exception as e:
        return _result("fail", filepath, ["event_schema_last_line"], [{"message": str(e)}], [])
    if schema_errs:
        return _result("fail", filepath, ["event_schema_last_line"], schema_errs, [])
    return _result("pass", filepath, ["event_schema_last_line"], [], [])


def check_test_plan(filepath):
    """Check test_plan.md for presence and validity of precision_config."""
    try:
        text = open(filepath).read()
    except Exception as e:
        return _result("fail", filepath, ["precision_config_schema"], [{"message": str(e)}], [])

    m = re.search(r"```yaml\s*(precision_config:.*?)```", text, re.DOTALL)
    if not m:
        return _result(
            "fail", filepath, ["precision_config_schema"],
            [{"type": "missing_precision_config",
              "message": "test_plan does not contain a precision_config YAML block"}],
            [],
        )

    try:
        import yaml
        cfg_root = yaml.safe_load(m.group(1))
        schema = load_schema("precision_config.schema.json")
        schema_errs = validate_against_schema(cfg_root, schema)
    except Exception as e:
        return _result("fail", filepath, ["precision_config_schema"], [{"message": str(e)}], [])

    if schema_errs:
        return _result("fail", filepath, ["precision_config_schema"], schema_errs, [])
    return _result("pass", filepath, ["precision_config_schema"], [], [])


# ── router ────────────────────────────────────────────────────────────────────

def route(filepath):
    fp = os.path.normpath(os.path.abspath(filepath))
    basename = os.path.basename(fp)
    parent = os.path.basename(os.path.dirname(fp))
    grandparent = os.path.basename(os.path.dirname(os.path.dirname(fp)))

    # Safety: never validate files inside HARNESS_ROOT as workspace files
    # (the harness itself isn't a tool workspace)
    ws_candidate = _detect_workspace(fp)

    if basename == "biogpu_project.yaml":
        ws = os.path.dirname(fp)
        if os.path.normpath(ws).startswith(HARNESS_ROOT):
            # harness template — skip
            return _result("pass", fp, ["skip"], [], ["harness template, not a tool workspace"])
        return check_biogpu_project(fp, ws)

    if basename == "task_state.json" and parent == "state":
        ws = os.path.dirname(os.path.dirname(fp))
        return check_task_state(fp, ws)

    if basename == "trace_context.json" and parent == "state":
        return check_trace_context(fp)

    if basename == "events.jsonl" and parent == "logs":
        return check_events_jsonl(fp)

    if basename.endswith("_test_plan.md") and parent == "test_plans" and grandparent == "reports":
        return check_test_plan(fp)

    # unrecognized file — pass silently
    return _result("pass", fp, ["skip"], [], [f"not a known BioGPU-Harness artifact, skipping"])


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="BioGPU PostToolUse validation hook")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="File path to validate (CLI / smoke test mode)")
    group.add_argument("--stdin", action="store_true", help="Read hook JSON from stdin")
    args = parser.parse_args()

    if args.stdin:
        try:
            hook_data = json.load(sys.stdin)
            filepath = (hook_data.get("tool_input", {}) or {}).get("file_path")
            if not filepath:
                # No file path in payload — silently pass (e.g. Bash tool)
                print(json.dumps({"status": "pass", "file": None, "checks": ["skip"], "errors": [], "warnings": ["no file_path in hook payload"]}))
                sys.exit(0)
        except Exception as e:
            print(json.dumps({"status": "error", "errors": [str(e)]}))
            sys.exit(2)
    else:
        filepath = args.file

    status = route(filepath)
    sys.exit(0 if status == "pass" else 1)


if __name__ == "__main__":
    main()
