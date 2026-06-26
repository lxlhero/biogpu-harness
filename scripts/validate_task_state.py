#!/usr/bin/env python3
"""Validate a state/task_state.json file."""

import argparse
import json
import os
import sys

VALID_MODES = {"A", "B"}

VALID_REQUEST_TYPES = {
    "from_scratch",
    "fix_accuracy",
    "fix_e2e_failure",
    "fix_module_test_failure",
    "fix_runtime_error",
    "fix_docker_or_rjob",
    "optimize_speed",
    "continue_next_module",
    "rerun_benchmark",
    "run_double_check",
    "write_final_report",
    "other",
}

VALID_NEXT_ACTIONS = {
    "initialize_project",
    "run_benchmark",
    "setup_source",
    "build_l1_image",
    "run_profiling",
    "assess_feasibility",
    "plan_primary_e2e",
    "run_primary_cpu_baseline",
    "plan_gpu_implementation",
    "implement_gpu_module",
    "review_gpu_code",
    "run_module_test",
    "diagnose_failure",
    "build_l2_image",
    "run_primary_gpu_compare",
    "ask_double_check",
    "plan_double_check_e2e",
    "run_double_check_e2e",
    "plan_existing_project",
    "write_final_report",
    "done",
    "blocked",
    "manual_review",
    "load_execution_plan",
}

REQUIRED_TOP = [
    "task_id", "tool_name", "mode",
    "current_step", "current_role", "current_module",
    "module_queue", "attempt", "max_attempts_per_module",
    "next_action", "last_result",
    "human_approval_required", "approval_reason", "approved",
    "tests", "session_request",
]

REQUIRED_TESTS_E2E = [
    "status", "benchmark_source", "benchmark_name", "benchmark_path",
    "plan_path", "input_manifest_path", "cpu_result_path",
    "gpu_result_path", "compare_report_path", "approved", "pass",
]

REQUIRED_SESSION_REQUEST = [
    "tool_name", "mode", "request_type", "summary", "user_notes",
    "allow_code_changes", "requires_execution_plan_approval",
]


def validate(state, filepath):
    errors = []
    warnings = []

    # Required top-level fields
    for key in REQUIRED_TOP:
        if key not in state:
            errors.append(f"Missing required field: {key}")

    if errors:
        return errors, warnings

    # mode
    mode = state.get("mode")
    if mode not in VALID_MODES:
        errors.append(f"mode must be one of {VALID_MODES}, got: {mode!r}")

    # next_action
    next_action = state.get("next_action")
    if next_action not in VALID_NEXT_ACTIONS:
        errors.append(f"next_action '{next_action}' is not a valid value; must be one of {sorted(VALID_NEXT_ACTIONS)}")

    # tests
    tests = state.get("tests", {})
    if not isinstance(tests, dict):
        errors.append("tests must be a dict")
    else:
        for suite in ("primary_e2e", "double_check_e2e"):
            if suite not in tests:
                errors.append(f"Missing required field: tests.{suite}")
            else:
                for key in REQUIRED_TESTS_E2E:
                    if key not in tests[suite]:
                        errors.append(f"Missing required field: tests.{suite}.{key}")

    # session_request
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
                errors.append(f"session_request.request_type '{rt}' is not valid; must be one of {sorted(VALID_REQUEST_TYPES)}")
            if not sr.get("tool_name"):
                errors.append("session_request.tool_name must not be empty in B mode")
            if not sr.get("summary"):
                warnings.append("session_request.summary is empty (recommended to fill in B mode)")
    elif mode == "A":
        # session_request may be null in A mode
        if sr is not None:
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

    if args.workspace:
        filepath = os.path.join(args.workspace, "state", "task_state.json")
    else:
        filepath = args.state

    try:
        with open(filepath) as f:
            state = json.load(f)
    except FileNotFoundError:
        result = {"status": "fail", "file": filepath, "errors": [f"File not found: {filepath}"], "warnings": []}
        print(json.dumps(result, indent=2))
        sys.exit(1)
    except json.JSONDecodeError as e:
        result = {"status": "error", "file": filepath, "errors": [f"Invalid JSON: {e}"], "warnings": []}
        print(json.dumps(result, indent=2))
        sys.exit(2)

    errors, warnings = validate(state, filepath)
    status = "pass" if not errors else "fail"
    result = {"status": status, "file": filepath, "errors": errors, "warnings": warnings}
    print(json.dumps(result, indent=2))
    sys.exit(0 if status == "pass" else 1)


if __name__ == "__main__":
    main()
