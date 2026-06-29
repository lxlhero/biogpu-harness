#!/usr/bin/env python3
"""Validate a biogpu_project.yaml file."""

import argparse
import json
import os
import sys

# allow running from any cwd by adding scripts/ to path
sys.path.insert(0, os.path.dirname(__file__))

try:
    import yaml
except ImportError:
    print(json.dumps({"status": "error", "schema_errors": [], "custom_errors": [],
                      "errors": ["PyYAML not installed: pip install pyyaml"], "warnings": []}))
    sys.exit(2)

from lib.schema_utils import load_schema, validate_against_schema

HARNESS_ROOT = os.path.normpath("/Users/huron/code/ai_lab/biogpu-harness")

REQUIRED_PATHS = [
    "workspace_path", "bio_tool_path", "state_path",
    "reports_path", "runs_path", "benchmarks_path",
    "baseline_path", "logs_path", "artifacts_path",
]


def _get(d, *keys):
    for k in keys:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def custom_validate(cfg):
    """Path-relationship checks that cannot be expressed in JSON Schema."""
    errors = []
    warnings = []

    paths = cfg.get("paths", {})
    workspace = paths.get("workspace_path", "")

    if workspace:
        ws_norm = os.path.normpath(workspace)
        if ws_norm == HARNESS_ROOT:
            errors.append("paths.workspace_path must not be the biogpu-harness root")
        if ws_norm.startswith(HARNESS_ROOT + os.sep):
            errors.append("paths.workspace_path must not be inside biogpu-harness")

        sub_paths = {k: paths.get(k, "") for k in REQUIRED_PATHS if k != "workspace_path"}
        for name, p in sub_paths.items():
            if p and not os.path.normpath(p).startswith(ws_norm):
                errors.append(f"paths.{name} must be under workspace_path")

        state = paths.get("state_path", "")
        expected_state_dir = os.path.join(ws_norm, "state")
        if state and not os.path.normpath(state).startswith(expected_state_dir):
            errors.append("paths.state_path must be under workspace_path/state/")

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

    filepath = (os.path.join(args.workspace, "biogpu_project.yaml")
                if args.workspace else args.project)

    try:
        with open(filepath) as f:
            cfg = yaml.safe_load(f)
    except FileNotFoundError:
        out = {"status": "fail", "file": filepath,
               "schema_errors": [], "custom_errors": [],
               "errors": [f"File not found: {filepath}"], "warnings": []}
        print(json.dumps(out, indent=2))
        sys.exit(1)
    except Exception as e:
        out = {"status": "error", "file": filepath,
               "schema_errors": [], "custom_errors": [],
               "errors": [f"Failed to parse YAML: {e}"], "warnings": []}
        print(json.dumps(out, indent=2))
        sys.exit(2)

    # ── 1. Schema validation ──────────────────────────────────────────────────
    try:
        schema = load_schema("biogpu_project.schema.json")
        schema_errors = validate_against_schema(cfg, schema)
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
    custom_errors, warnings = custom_validate(cfg)

    all_errors = [e for e in custom_errors]
    status = "pass" if not all_errors else "fail"
    out = {
        "status": status,
        "file": filepath,
        "schema_errors": [],
        "custom_errors": custom_errors,
        "errors": all_errors,
        "warnings": warnings,
    }
    print(json.dumps(out, indent=2))
    sys.exit(0 if status == "pass" else 1)


if __name__ == "__main__":
    main()
