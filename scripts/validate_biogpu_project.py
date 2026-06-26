#!/usr/bin/env python3
"""Validate a biogpu_project.yaml file."""

import argparse
import json
import os
import sys

try:
    import yaml
except ImportError:
    print(json.dumps({"status": "error", "errors": ["PyYAML not installed: pip install pyyaml"], "warnings": []}))
    sys.exit(2)

HARNESS_ROOT = "/Users/huron/code/ai_lab/biogpu-harness"

VALID_MODES = {"A", "B"}
VALID_ENTRYPOINTS = {"/bio-gpu-team"}
VALID_SOURCE_STATUS = {"pending", "ready", "failed", "user_provided"}
VALID_INSTALL_METHODS = {"auto", "git", "github", "gitcode", "pip", "conda", "local", "archive", "unknown"}
VALID_PRECISION_POLICIES = {"auto", "planned", "approved", "fixed"}

REQUIRED_TOP = ["tool_name", "mode", "harness", "paths", "source", "user_request", "benchmarks", "precision"]
REQUIRED_HARNESS = ["root", "entrypoint", "version"]
REQUIRED_PATHS = [
    "workspace_path", "bio_tool_path", "state_path",
    "reports_path", "runs_path", "benchmarks_path",
    "baseline_path", "logs_path", "artifacts_path",
]
REQUIRED_SOURCE = ["status", "user_specified_source", "source_url", "version", "install_method"]
REQUIRED_USER_REQUEST = ["summary", "priority", "speedup_target", "notes"]
REQUIRED_BENCHMARKS_E2E = ["status"]
REQUIRED_PRECISION = ["policy", "decided_by", "plan_path"]


def _get(d, *keys):
    for k in keys:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def validate(cfg, filepath):
    errors = []
    warnings = []

    # Top-level required keys
    for key in REQUIRED_TOP:
        if key not in cfg:
            errors.append(f"Missing required field: {key}")

    if errors:
        return errors, warnings

    # harness
    harness = cfg.get("harness", {})
    for key in REQUIRED_HARNESS:
        if key not in harness:
            errors.append(f"Missing required field: harness.{key}")
    if harness.get("entrypoint") not in VALID_ENTRYPOINTS:
        errors.append(f"harness.entrypoint must be one of {VALID_ENTRYPOINTS}, got: {harness.get('entrypoint')!r}")

    # mode
    mode = cfg.get("mode")
    if mode not in VALID_MODES:
        errors.append(f"mode must be one of {VALID_MODES}, got: {mode!r}")

    # paths
    paths = cfg.get("paths", {})
    for key in REQUIRED_PATHS:
        if key not in paths:
            errors.append(f"Missing required field: paths.{key}")

    workspace = paths.get("workspace_path", "")
    if workspace:
        harness_root = os.path.normpath(HARNESS_ROOT)
        ws_norm = os.path.normpath(workspace)
        if ws_norm == harness_root:
            errors.append("paths.workspace_path must not be the biogpu-harness root")
        if ws_norm.startswith(harness_root + os.sep):
            errors.append("paths.workspace_path must not be inside biogpu-harness")

        # sub-path checks
        sub_paths = {
            "bio_tool_path": paths.get("bio_tool_path", ""),
            "state_path": paths.get("state_path", ""),
            "reports_path": paths.get("reports_path", ""),
            "runs_path": paths.get("runs_path", ""),
            "benchmarks_path": paths.get("benchmarks_path", ""),
            "baseline_path": paths.get("baseline_path", ""),
            "logs_path": paths.get("logs_path", ""),
            "artifacts_path": paths.get("artifacts_path", ""),
        }
        for name, p in sub_paths.items():
            if p and not os.path.normpath(p).startswith(ws_norm):
                errors.append(f"paths.{name} must be under workspace_path")

        state = paths.get("state_path", "")
        expected_state_dir = os.path.join(ws_norm, "state")
        if state and not os.path.normpath(state).startswith(expected_state_dir):
            errors.append(f"paths.state_path must be under workspace_path/state/")

    # source
    source = cfg.get("source", {})
    for key in REQUIRED_SOURCE:
        if key not in source:
            errors.append(f"Missing required field: source.{key}")
    if source.get("status") not in VALID_SOURCE_STATUS:
        errors.append(f"source.status must be one of {VALID_SOURCE_STATUS}, got: {source.get('status')!r}")
    if source.get("install_method") not in VALID_INSTALL_METHODS:
        errors.append(f"source.install_method must be one of {VALID_INSTALL_METHODS}, got: {source.get('install_method')!r}")

    # user_request
    user_request = cfg.get("user_request", {})
    for key in REQUIRED_USER_REQUEST:
        if key not in user_request:
            errors.append(f"Missing required field: user_request.{key}")

    # benchmarks
    benchmarks = cfg.get("benchmarks", {})
    for suite in ("primary_e2e", "double_check_e2e"):
        if suite not in benchmarks:
            errors.append(f"Missing required field: benchmarks.{suite}")
        else:
            for key in REQUIRED_BENCHMARKS_E2E:
                if key not in benchmarks[suite]:
                    errors.append(f"Missing required field: benchmarks.{suite}.{key}")

    # precision
    precision = cfg.get("precision", {})
    for key in REQUIRED_PRECISION:
        if key not in precision:
            errors.append(f"Missing required field: precision.{key}")
    if precision.get("policy") not in VALID_PRECISION_POLICIES:
        errors.append(f"precision.policy must be one of {VALID_PRECISION_POLICIES}, got: {precision.get('policy')!r}")

    # warnings
    if not cfg.get("tool_name"):
        warnings.append("tool_name is empty")
    if not _get(cfg, "user_request", "summary"):
        warnings.append("user_request.summary is empty")

    return errors, warnings


def main():
    parser = argparse.ArgumentParser(description="Validate biogpu_project.yaml")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--workspace", help="Path to workspace directory")
    group.add_argument("--project", help="Path to biogpu_project.yaml")
    args = parser.parse_args()

    if args.workspace:
        filepath = os.path.join(args.workspace, "biogpu_project.yaml")
    else:
        filepath = args.project

    try:
        with open(filepath) as f:
            cfg = yaml.safe_load(f)
    except FileNotFoundError:
        result = {"status": "fail", "file": filepath, "errors": [f"File not found: {filepath}"], "warnings": []}
        print(json.dumps(result, indent=2))
        sys.exit(1)
    except Exception as e:
        result = {"status": "error", "file": filepath, "errors": [f"Failed to parse YAML: {e}"], "warnings": []}
        print(json.dumps(result, indent=2))
        sys.exit(2)

    errors, warnings = validate(cfg, filepath)
    status = "pass" if not errors else "fail"
    result = {"status": status, "file": filepath, "errors": errors, "warnings": warnings}
    print(json.dumps(result, indent=2))
    sys.exit(0 if status == "pass" else 1)


if __name__ == "__main__":
    main()
