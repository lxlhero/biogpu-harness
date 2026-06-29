#!/usr/bin/env python3
"""BioGPU-Harness local CI: validates harness control-plane health."""

import argparse
import json
import os
import re
import subprocess
import sys

HARNESS_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PYTHON = sys.executable
SCRIPTS = os.path.join(HARNESS_ROOT, "scripts")

DEFAULT_WORKSPACE = "/Users/huron/code/ai_lab/transfer2gpu/_phase2_dryrun_tool"

SCHEMA_FILES = [
    "schemas/biogpu_project.schema.json",
    "schemas/task_state.schema.json",
    "schemas/trace_context.schema.json",
    "schemas/event.schema.json",
    "schemas/precision_config.schema.json",
]

OLD_PATH_PATTERNS = [
    "bioinformatics-tool-gpu-ification",
    ".claude/knowledge/bioinformatics-tool-gpu",
    "SKILL.md.bak",
]

ACTIVE_DIRS = [
    ".claude",
    "scripts",
    "schemas",
    "templates",
    "skills",
    "docs/architecture",
    "docs/usage",
]
ACTIVE_FILES = ["README.md", "CLAUDE.md", "harness_config.yaml"]

EXPECTED_FAIL_GATES = []  # (gate, test_suite, expected_status)


# ── helpers ───────────────────────────────────────────────────────────────────

def run(cmd, **kwargs):
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


def check(name, status, message="", **extra):
    c = {"name": name, "status": status}
    if message:
        c["message"] = message
    c.update(extra)
    return c


# ── 3.1 schema parse ──────────────────────────────────────────────────────────

def check_schema_parse():
    errors = []
    for rel in SCHEMA_FILES:
        path = os.path.join(HARNESS_ROOT, rel)
        try:
            with open(path) as f:
                json.load(f)
        except Exception as e:
            errors.append(f"{rel}: {e}")
    if errors:
        return check("schema_parse", "fail", "; ".join(errors))
    return check("schema_parse", "pass", f"all {len(SCHEMA_FILES)} schemas parsed")


# ── 3.2 validators ────────────────────────────────────────────────────────────

def check_validators(workspace):
    errors = []
    for script in ("validate_biogpu_project.py", "validate_task_state.py"):
        r = run([PYTHON, os.path.join(SCRIPTS, script), "--workspace", workspace])
        if r.returncode != 0:
            try:
                data = json.loads(r.stdout)
                errs = data.get("errors", [r.stdout[:200]])
            except Exception:
                errs = [r.stdout[:200]]
            errors.append(f"{script}: {errs}")
    if errors:
        return check("validators", "fail", "; ".join(str(e) for e in errors))
    return check("validators", "pass", "validate_biogpu_project + validate_task_state passed")


# ── 3.3 hook_validate_file ────────────────────────────────────────────────────

def check_hook(workspace):
    errors = []
    hook_script = os.path.join(SCRIPTS, "hook_validate_file.py")

    # critical files — expect pass
    critical = [
        os.path.join(workspace, "biogpu_project.yaml"),
        os.path.join(workspace, "state/task_state.json"),
        os.path.join(workspace, "state/trace_context.json"),
        os.path.join(workspace, "logs/events.jsonl"),
        os.path.join(workspace, "reports/test_plans/phase2_2_clean_test_plan.md"),
    ]
    for f in critical:
        r = run([PYTHON, hook_script, "--file", f])
        try:
            data = json.loads(r.stdout)
            status = data.get("status")
        except Exception:
            status = "error"
        if status not in ("pass", "skipped"):
            errors.append(f"{os.path.basename(f)}: {status} — {data.get('errors', [])[:1]}")

    # non-critical — expect skipped
    readme = os.path.join(HARNESS_ROOT, "README.md")
    r = run([PYTHON, hook_script, "--file", readme])
    try:
        data = json.loads(r.stdout)
        if data.get("status") != "skipped":
            errors.append(f"README.md should be skipped, got: {data.get('status')}")
    except Exception as e:
        errors.append(f"README.md hook error: {e}")

    if errors:
        return check("hook_validate_file", "fail", "; ".join(str(e) for e in errors))
    return check("hook_validate_file", "pass", "5 critical files pass, README skipped")


# ── 3.4 compare_precision ────────────────────────────────────────────────────

def check_compare_precision(workspace):
    errors = []
    test_plan = os.path.join(workspace, "reports/test_plans/phase2_2_clean_test_plan.md")
    out_json = os.path.join(workspace, "reports/test_results/phase2_5_ci_precision.json")
    out_md = os.path.join(workspace, "reports/test_results/phase2_5_ci_precision.md")

    if not os.path.isfile(test_plan):
        return check("compare_precision", "fail", f"test plan not found: {test_plan}")

    r = run([PYTHON, os.path.join(SCRIPTS, "compare_precision.py"),
             "--workspace", workspace,
             "--test-plan", test_plan,
             "--out-json", out_json,
             "--out-md", out_md])
    if r.returncode != 0:
        try:
            data = json.loads(r.stdout)
            errors.append(f"clean case fail: {data.get('errors', [])}")
        except Exception:
            errors.append(f"clean case failed (exit {r.returncode}): {r.stdout[:200]}")

    if errors:
        return check("compare_precision", "fail", "; ".join(str(e) for e in errors))
    return check("compare_precision", "pass", "clean case passed")


# ── 3.5 completion gate ──────────────────────────────────────────────────────

def check_completion_gates(workspace):
    errors = []
    warnings = []
    gate_script = os.path.join(SCRIPTS, "check_completion_gate.py")

    # expected-pass gates
    pass_cases = [
        (["--gate", "project_init"], "project_init"),
        (["--gate", "test_plan", "--test-suite", "phase2_2_clean"], "test_plan/phase2_2_clean"),
        (["--gate", "primary_e2e", "--test-suite", "phase2_2_clean"], "primary_e2e/phase2_2_clean"),
        (["--gate", "double_check_e2e"], "double_check_e2e"),
    ]
    for extra_args, label in pass_cases:
        r = run([PYTHON, gate_script, "--workspace", workspace] + extra_args)
        try:
            data = json.loads(r.stdout)
            status = data.get("status")
        except Exception:
            status = "error"
        if status not in ("pass", "skipped"):
            errors.append(f"gate {label}: expected pass/skipped, got {status}")

    # expected-fail negative case (phase2_1 has injected anomaly)
    r = run([PYTHON, gate_script, "--workspace", workspace,
             "--gate", "primary_e2e", "--test-suite", "phase2_1"])
    try:
        data = json.loads(r.stdout)
        status = data.get("status")
        next_agent = data.get("recommended_next_agent")
    except Exception:
        status = "error"
        next_agent = None
    if status == "fail" and next_agent == "bio-gpu-trace-analyst-agent":
        warnings.append("expected_fail: primary_e2e/phase2_1 → fail → trace-analyst (correct)")
    else:
        errors.append(f"expected_fail case: got status={status}, next_agent={next_agent}")

    if errors:
        return check("completion_gates", "fail", "; ".join(errors), warnings=warnings)
    return check("completion_gates", "pass",
                 "project_init/test_plan/primary_e2e_clean/double_check_e2e passed; negative phase2_1 is expected_fail",
                 warnings=warnings)


# ── 3.6 old path check ───────────────────────────────────────────────────────

def check_old_paths():
    errors = []
    warnings = []
    this_script = os.path.abspath(__file__)

    # Contexts in which an old-path reference is acceptable (prohibition / rename / archive)
    ACCEPTABLE_CONTEXTS = [
        "不使用旧路径", "不使用无效路径", "Do not use deprecated", "deprecated",
        "invalid", "must not", "→", "原 ", "重命名", "archive", "已删除",
        "bioinformatics-tool-gpu-skills", "OLD_PATH_PATTERNS",  # CI self-reference
    ]

    def is_acceptable_in_context(lines, idx):
        """Return True if line idx is surrounded by acceptable context (±3 lines)."""
        window_start = max(0, idx - 3)
        window_end = min(len(lines), idx + 4)
        context = "".join(lines[window_start:window_end])
        return any(ctx in context for ctx in ACCEPTABLE_CONTEXTS)

    def grep_in(path, pattern):
        """Return lines that contain pattern AND are NOT in acceptable contexts."""
        hits = []
        if os.path.isfile(path) and path != this_script:
            try:
                file_lines = open(path, errors="replace").readlines()
                bad_lines = [
                    file_lines[i].rstrip()
                    for i in range(len(file_lines))
                    if pattern in file_lines[i] and not is_acceptable_in_context(file_lines, i)
                ]
                if bad_lines:
                    hits = bad_lines
            except Exception:
                pass
        elif os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
                for fname in files:
                    fp = os.path.join(root, fname)
                    if fp == this_script:
                        continue
                    try:
                        file_lines = open(fp, errors="replace").readlines()
                        bad_lines = [
                            file_lines[i].rstrip()
                            for i in range(len(file_lines))
                            if pattern in file_lines[i] and not is_acceptable_in_context(file_lines, i)
                        ]
                        if bad_lines:
                            hits.append((fp, bad_lines))
                    except Exception:
                        pass
        return hits

    for pattern in OLD_PATH_PATTERNS:
        bad_hits = []
        history_count = 0

        for target in ACTIVE_DIRS + ACTIVE_FILES:
            raw = grep_in(os.path.join(HARNESS_ROOT, target), pattern)
            for item in raw:
                if isinstance(item, tuple):
                    fp, lines = item
                    # docs/optimize and docs/archive are historical — warn only
                    if "docs/optimize" in fp or "docs/archive" in fp or "docs/architecture" in fp:
                        history_count += 1
                    else:
                        bad_hits.append(f"{fp}: {lines[:1]}")
                else:
                    # single file line hit (file-level check)
                    bad_hits.append(item)

        if bad_hits:
            errors.append(f"'{pattern}' active ref: {bad_hits[:3]}")
        if history_count:
            warnings.append(f"'{pattern}' in docs only (ok): {history_count} file(s)")

    if errors:
        return check("old_path_check", "fail", "; ".join(errors))
    return check("old_path_check", "pass",
                 "no active old-path references outside prohibition rules / historical docs",
                 warnings=warnings)


# ── 3.7 agent / command structure ────────────────────────────────────────────

def check_structure():
    errors = []

    # commands
    for fname in ("bio-gpu-team.md", "bio-gpu-project-init.md"):
        path = os.path.join(HARNESS_ROOT, ".claude/commands", fname)
        try:
            text = open(path).read()
        except FileNotFoundError:
            errors.append(f"command {fname} not found")
            continue
        for marker in ("Resource Layer Policy", "/bio-gpu-team"):
            if marker not in text:
                errors.append(f"command {fname}: missing '{marker}'")

    # agents
    agents_dir = os.path.join(HARNESS_ROOT, ".claude/agents")
    agent_files = [f for f in os.listdir(agents_dir) if f.endswith(".md")]
    for fname in agent_files:
        path = os.path.join(agents_dir, fname)
        text = open(path).read()
        for marker in ("Resource Layer Policy", "Always read", "Read on demand"):
            if marker not in text:
                errors.append(f"agent {fname}: missing '{marker}'")

    if errors:
        return check("structure_check", "fail", "; ".join(errors[:5]))
    return check("structure_check", "pass",
                 f"2 commands + {len(agent_files)} agents have required sections")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="BioGPU-Harness CI")
    parser.add_argument("--workspace", default=DEFAULT_WORKSPACE)
    args = parser.parse_args()

    ws = args.workspace
    print(f"[CI] workspace: {ws}", file=sys.stderr)
    print(f"[CI] harness:   {HARNESS_ROOT}", file=sys.stderr)

    checks = [
        check_schema_parse(),
        check_validators(ws),
        check_hook(ws),
        check_compare_precision(ws),
        check_completion_gates(ws),
        check_old_paths(),
        check_structure(),
    ]

    errors = [c for c in checks if c["status"] == "fail"]
    all_warnings = []
    for c in checks:
        all_warnings.extend(c.pop("warnings", []))

    overall = "pass" if not errors else "fail"
    result = {
        "status": overall,
        "checks": checks,
        "errors": [{"check": c["name"], "message": c.get("message", "")} for c in errors],
        "warnings": all_warnings,
    }

    print(json.dumps(result, indent=2))
    sys.exit(0 if overall == "pass" else 1)


if __name__ == "__main__":
    main()
