#!/usr/bin/env python3
"""Validate a state/task_state.json file."""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from lib.schema_utils import load_schema, validate_against_schema

VALID_MODES = {"A", "B"}

VALID_REQUEST_TYPES = {
    "from_scratch", "fix_accuracy", "fix_e2e_failure", "fix_module_test_failure",
    "fix_runtime_error", "fix_docker_or_rjob", "optimize_speed", "continue_next_module",
    "rerun_benchmark", "run_double_check", "write_final_report", "other",
}

VALID_NEXT_ACTIONS = {
    "initialize_project", "run_benchmark", "setup_source", "build_l1_image",
    "run_profiling", "assess_feasibility", "plan_primary_e2e",
    "run_primary_cpu_baseline", "plan_gpu_implementation", "implement_gpu_module",
    "review_gpu_code", "run_module_test", "diagnose_failure", "build_l2_image",
    "run_primary_gpu_compare", "ask_double_check", "plan_double_check_e2e",
    "run_double_check_e2e", "plan_existing_project", "write_final_report",
    "done", "blocked", "manual_review", "load_execution_plan",
}

REQUIRED_TESTS_E2E = [
    "status", "benchmark_source", "benchmark_name", "benchmark_path",
    "plan_path", "input_manifest_path", "cpu_result_path",
    "gpu_result_path", "compare_report_path", "approved", "pass",
]

REQUIRED_SESSION_REQUEST = [
    "tool_name", "mode", "request_type", "summary", "user_notes",
    "allow_code_changes", "requires_execution_plan_approval",
]


def custom_validate(state):
    """Workflow-logic checks that go beyond JSON Schema constraints."""
    errors = []
    warnings = []

    mode = state.get("mode")

    # next_action whitelist (schema already covers enum, but belt-and-suspenders)
    next_action = state.get("next_action")
    if next_action is not None and next_action not in VALID_NEXT_ACTIONS:
        errors.append(f"next_action '{next_action}' is not a valid value; "
                      f"must be one of {sorted(VALID_NEXT_ACTIONS)}")

    # tests sub-fields
    tests = state.get("tests", {})
    if isinstance(tests, dict):
        for suite in ("primary_e2e", "double_check_e2e"):
            if suite in tests:
                for key in REQUIRED_TESTS_E2E:
                    if key not in tests[suite]:
                        errors.append(f"Missing required field: tests.{suite}.{key}")

    # session_request mode-specific rules
    sr = state.get("session_request")
    if mode == "B":
        if sr is None:
            errors.append("session_request must not be null in B mode")
        else:
            for key in REQUIRED_SESSION_REQUEST:
                if key not in sr:
                    errors.append(f"Missing required field: session_request.{key}")
            if sr.get("mode") != "B":
                errors.append(f"session_request.mode must be 'B', got: {sr.get('mode')!r}")
            rt = sr.get("request_type")
            if rt not in VALID_REQUEST_TYPES:
                errors.append(f"session_request.request_type '{rt}' is not valid; "
                               f"must be one of {sorted(VALID_REQUEST_TYPES)}")
            if not sr.get("tool_name"):
                errors.append("session_request.tool_name must not be empty in B mode")
            if not sr.get("summary"):
                warnings.append("session_request.summary is empty (recommended to fill in B mode)")
    elif mode == "A" and sr is not None:
        for key in REQUIRED_SESSION_REQUEST:
            if key not in sr:
                errors.append(f"Missing required field: session_request.{key}")
        rt = sr.get("request_type")
        if rt and rt not in VALID_REQUEST_TYPES:
            errors.append(f"session_request.request_type '{rt}' is not valid")

    # attempt sanity
    attempt = state.get("attempt")
    max_attempts = state.get("max_attempts_per_module")
    if isinstance(attempt, int) and isinstance(max_attempts, int) and attempt > max_attempts:
        warnings.append(f"attempt ({attempt}) exceeds max_attempts_per_module ({max_attempts})")

    return errors, warnings


def main():
    parser = argparse.ArgumentParser(description="Validate state/task_state.json")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--workspace", help="Path to workspace directory")
    group.add_argument("--state", help="Path to task_state.json")
    args = parser.parse_args()

    filepath = (os.path.join(args.workspace, "state", "task_state.json")
                if args.workspace else args.state)

    try:
        with open(filepath) as f:
            state = json.load(f)
    except FileNotFoundError:
        out = {"status": "fail", "file": filepath,
               "schema_errors": [], "custom_errors": [],
               "errors": [f"File not found: {filepath}"], "warnings": []}
        print(json.dumps(out, indent=2))
        sys.exit(1)
    except json.JSONDecodeError as e:
        out = {"status": "error", "file": filepath,
               "schema_errors": [], "custom_errors": [],
               "errors": [f"Invalid JSON: {e}"], "warnings": []}
        print(json.dumps(out, indent=2))
        sys.exit(2)

    # ── 1. Schema validation ──────────────────────────────────────────────────
    try:
        schema = load_schema("task_state.schema.json")
        schema_errors = validate_against_schema(state, schema)
    except Exception as e:
        out = {"status": "error", "file": filepath,
               "schema_errors": [], "custom_errors": [],
               "errors": [f"Schema validation error: {e}"], "warnings": []}
        print(json.dumps(out, indent=2))
        sys.exit(2)

    if schema_errors:
        out = {"status": "fail", "file": filepath,
               "schema_errors": schema_errors, "custom_errors": [],
               "errors": [e["message"] for e in schema_errors], "warnings": []}
        print(json.dumps(out, indent=2))
        sys.exit(1)

    # ── 2. Custom validation ──────────────────────────────────────────────────
    custom_errors, warnings = custom_validate(state)

    # ── 3. Phase gate validation (A mode only) ────────────────────────────────
    workspace = args.workspace if args.workspace else os.path.dirname(os.path.dirname(filepath))
    try:
        from check_phase_gate import check_gate
        gate_violations = check_gate(state, workspace)
    except ImportError:
        gate_violations = []
        warnings.append("check_phase_gate.py not found — phase gate skipped")

    all_errors = custom_errors + gate_violations
    status = "pass" if not all_errors else "fail"
    out = {
        "status": status,
        "file": filepath,
        "schema_errors": [],
        "custom_errors": custom_errors,
        "gate_violations": gate_violations,
        "errors": all_errors,
        "warnings": warnings,
    }
    print(json.dumps(out, indent=2))
    sys.exit(0 if status == "pass" else 1)


if __name__ == "__main__":
    main()
