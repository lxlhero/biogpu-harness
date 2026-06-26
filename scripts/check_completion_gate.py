#!/usr/bin/env python3
"""Check whether a workflow stage is truly complete (artifact + evidence gate)."""

import argparse
import json
import os
import re
import subprocess
import sys

HARNESS_ROOT = os.path.normpath("/Users/huron/code/ai_lab/biogpu-harness")
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))

VALID_GATES = {"project_init", "test_plan", "primary_e2e", "double_check_e2e", "final_delivery"}


# ── helpers ───────────────────────────────────────────────────────────────────

def err(type_, field, message):
    return {"type": type_, "field": field, "message": message}


def run_validator(script, workspace):
    r = subprocess.run(
        [sys.executable, os.path.join(SCRIPTS_DIR, script), "--workspace", workspace],
        capture_output=True, text=True,
    )
    try:
        result = json.loads(r.stdout)
    except Exception:
        result = {}
    return r.returncode, result


def run_log_event(workspace, gate, status, message):
    """Best-effort: log gate_checked event; ignore failures."""
    try:
        subprocess.run(
            [
                sys.executable, os.path.join(SCRIPTS_DIR, "log_event.py"),
                "--workspace", workspace,
                "--agent", "check_completion_gate.py",
                "--event-type", "gate_checked",
                "--status", status,
                "--step", gate,
                "--message", message,
            ],
            capture_output=True, text=True, timeout=15,
        )
    except Exception:
        pass


def load_yaml_cfg(workspace):
    try:
        import yaml
        with open(os.path.join(workspace, "biogpu_project.yaml")) as f:
            return yaml.safe_load(f)
    except Exception:
        return {}


def load_task_state(workspace):
    try:
        with open(os.path.join(workspace, "state", "task_state.json")) as f:
            return json.load(f)
    except Exception:
        return {}


def load_trace_ctx(workspace):
    try:
        with open(os.path.join(workspace, "state", "trace_context.json")) as f:
            return json.load(f)
    except Exception:
        return None


def load_events(workspace):
    path = os.path.join(workspace, "logs", "events.jsonl")
    events = []
    if not os.path.isfile(path):
        return events
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except Exception:
                    pass
    return events


def extract_precision_config(md_path):
    try:
        text = open(md_path).read()
        m = re.search(r"```yaml\s*(precision_config:.*?)```", text, re.DOTALL)
        if not m:
            return None
        import yaml
        return yaml.safe_load(m.group(1))
    except Exception:
        return None


def result(status, gate, workspace, test_suite, errors, warnings, evidence, next_agent, next_action, **extra):
    out = {
        "status": status,
        "gate": gate,
        "workspace": workspace,
        "errors": errors,
        "warnings": warnings,
        "evidence": evidence,
        "recommended_next_agent": next_agent,
        "recommended_next_action": next_action,
    }
    if test_suite:
        out["test_suite"] = test_suite
    out.update(extra)
    return out


# ── pre-checks (all gates) ────────────────────────────────────────────────────

def pre_checks(workspace):
    errors = []

    for fname in ("biogpu_project.yaml", "state/task_state.json",
                  "state/trace_context.json", "logs/events.jsonl"):
        if not os.path.isfile(os.path.join(workspace, fname)):
            errors.append(err("missing_file", fname, f"{fname} does not exist"))

    if errors:
        return errors

    for script in ("validate_biogpu_project.py", "validate_task_state.py"):
        rc, res = run_validator(script, workspace)
        if rc != 0:
            for e in res.get("errors", []):
                errors.append(err("validator_fail", script, e))

    return errors


# ── gate implementations ──────────────────────────────────────────────────────

def gate_project_init(workspace, test_suite, cfg, state, trace_ctx):
    errors, warnings, evidence = [], [], []

    if not trace_ctx:
        errors.append(err("missing_file", "state/trace_context.json", "trace_context.json missing"))
    else:
        for field in ("trace_id", "session_id", "root_span_id"):
            if not trace_ctx.get(field):
                errors.append(err("missing_field", f"trace_context.{field}", f"{field} is empty"))

    ws = cfg.get("paths", {}).get("workspace_path", "")
    if ws:
        ws_norm = os.path.normpath(ws)
        if ws_norm == HARNESS_ROOT or ws_norm.startswith(HARNESS_ROOT + os.sep):
            errors.append(err("invalid_path", "workspace_path", "workspace must not be inside HARNESS_ROOT"))

    evidence += ["biogpu_project.yaml", "state/task_state.json", "state/trace_context.json"]

    mode = cfg.get("mode", state.get("mode"))
    next_action = "plan_existing_project" if mode == "B" else "run_benchmark"

    if errors:
        return result("fail", "project_init", workspace, test_suite, errors, warnings, evidence,
                      "bio-gpu-trace-analyst-agent", None)
    return result("pass", "project_init", workspace, test_suite, errors, warnings, evidence,
                  None, next_action)


def gate_test_plan(workspace, test_suite, cfg, state, trace_ctx):
    errors, warnings, evidence = [], [], []
    suite = test_suite or "primary_e2e"
    plan_path = os.path.join(workspace, f"reports/test_plans/{suite}_test_plan.md")

    if not os.path.isfile(plan_path):
        errors.append(err("missing_artifact", f"reports/test_plans/{suite}_test_plan.md",
                          "test plan does not exist"))
        return result("fail", "test_plan", workspace, test_suite, errors, warnings, evidence,
                      "bio-gpu-test-planner-agent", f"plan_{suite.replace('_e2e','')}_e2e" if "e2e" in suite else "plan_primary_e2e")

    evidence.append(f"reports/test_plans/{suite}_test_plan.md")
    pc_root = extract_precision_config(plan_path)

    if pc_root is None:
        errors.append(err("missing_precision_config", plan_path,
                          "test_plan does not contain precision_config block"))
        return result("fail", "test_plan", workspace, test_suite, errors, warnings, evidence,
                      "bio-gpu-test-planner-agent", None)

    pc = pc_root.get("precision_config", pc_root)
    metrics = pc.get("metrics", [])
    if not metrics:
        errors.append(err("empty_metrics", "precision_config.metrics", "no metrics defined"))
    else:
        for m in metrics:
            if not m.get("name"):
                errors.append(err("missing_field", "metric.name", "metric missing name"))
            needs_files = m.get("name") not in ("file_exists",)
            if needs_files:
                if not m.get("cpu_file") and m.get("name") not in ("file_exists",):
                    warnings.append(f"metric '{m.get('name')}' missing cpu_file")
                if not m.get("gpu_file") and m.get("name") not in ("file_exists",):
                    warnings.append(f"metric '{m.get('name')}' missing gpu_file")
            no_threshold_needed = m.get("name") in ("exact_match", "row_count_match", "file_exists")
            if not no_threshold_needed and not m.get("threshold") and not m.get("threshold_low"):
                warnings.append(f"metric '{m.get('name')}' missing threshold")
            if not no_threshold_needed and not m.get("direction"):
                warnings.append(f"metric '{m.get('name')}' missing direction")

    if errors:
        return result("fail", "test_plan", workspace, test_suite, errors, warnings, evidence,
                      "bio-gpu-test-planner-agent", None)
    return result("pass", "test_plan", workspace, test_suite, errors, warnings, evidence,
                  None, "run_primary_cpu_baseline")


def gate_primary_e2e(workspace, test_suite, cfg, state, trace_ctx, events):
    errors, warnings, evidence = [], [], []
    suite = test_suite or "primary_e2e"

    plan_path = f"reports/test_plans/{suite}_test_plan.md"
    prec_json = f"reports/test_results/{suite}_precision.json"
    prec_md = f"reports/test_results/{suite}_precision.md"

    if not os.path.isfile(os.path.join(workspace, plan_path)):
        errors.append(err("missing_artifact", plan_path, "test plan missing"))
    else:
        evidence.append(plan_path)

    missing_prec = not os.path.isfile(os.path.join(workspace, prec_json))
    if missing_prec:
        errors.append(err("missing_artifact", prec_json, "precision result is missing"))
    else:
        evidence.append(prec_json)
        try:
            with open(os.path.join(workspace, prec_json)) as f:
                prec_data = json.load(f)
            if prec_data.get("status") != "pass":
                errors.append(err("precision_fail", prec_json,
                                  f"precision.json status={prec_data.get('status')!r}, expected pass"))
        except Exception as e:
            errors.append(err("parse_error", prec_json, str(e)))

    if not os.path.isfile(os.path.join(workspace, prec_md)):
        warnings.append(f"{prec_md} does not exist")
    else:
        evidence.append(prec_md)

    # check event evidence
    relevant = [
        e for e in events
        if e.get("event_type") in ("test_completed", "command_executed")
        and e.get("status") == "pass"
    ]
    if not relevant:
        errors.append(err("missing_event", "logs/events.jsonl",
                          "no test_completed or command_executed pass event found"))
    else:
        evidence.append("logs/events.jsonl")
        for ev in relevant:
            for field in ("trace_id", "session_id", "span_id"):
                if not ev.get(field):
                    warnings.append(f"event {ev.get('event_id')} missing {field}")
            ap = ev.get("artifact_path")
            if ap and not os.path.isfile(os.path.join(workspace, ap)):
                errors.append(err("missing_artifact", ap,
                                  f"event declares artifact_path but file does not exist"))

    if errors:
        next_agent = "bio-gpu-test-runner-agent" if missing_prec else "bio-gpu-trace-analyst-agent"
        return result("fail", "primary_e2e", workspace, test_suite, errors, warnings, evidence,
                      next_agent, "run_primary_gpu_compare")
    return result("pass", "primary_e2e", workspace, test_suite, errors, warnings, evidence,
                  None, "ask_double_check")


def gate_double_check_e2e(workspace, test_suite, cfg, state, trace_ctx, events):
    errors, warnings, evidence = [], [], []
    dc_status = cfg.get("benchmarks", {}).get("double_check_e2e", {}).get("status", "not_requested")

    if dc_status == "not_requested":
        return {
            "status": "skipped",
            "gate": "double_check_e2e",
            "workspace": workspace,
            "reason": "double_check_e2e not requested",
            "errors": [], "warnings": [], "evidence": [],
            "recommended_next_agent": None,
            "recommended_next_action": None,
        }

    suite = test_suite or "double_check_e2e"
    plan_path = f"reports/test_plans/{suite}_test_plan.md"
    prec_json = f"reports/test_results/{suite}_precision.json"

    if not os.path.isfile(os.path.join(workspace, plan_path)):
        errors.append(err("missing_artifact", plan_path, "double_check test plan missing"))
    else:
        evidence.append(plan_path)

    if not os.path.isfile(os.path.join(workspace, prec_json)):
        errors.append(err("missing_artifact", prec_json, "double_check precision result missing"))
    else:
        evidence.append(prec_json)
        try:
            with open(os.path.join(workspace, prec_json)) as f:
                prec_data = json.load(f)
            if prec_data.get("status") != "pass":
                errors.append(err("precision_fail", prec_json,
                                  f"double_check precision status={prec_data.get('status')!r}"))
        except Exception as e:
            errors.append(err("parse_error", prec_json, str(e)))

    # check event
    dc_events = [
        e for e in events
        if e.get("event_type") in ("test_completed",) and e.get("status") == "pass"
        and "double_check" in (e.get("step") or "")
    ]
    if not dc_events:
        warnings.append("no double_check test_completed pass event found in events.jsonl")
    else:
        evidence.append("logs/events.jsonl")

    if errors:
        return result("fail", "double_check_e2e", workspace, suite, errors, warnings, evidence,
                      "bio-gpu-test-runner-agent", "run_double_check_e2e")
    return result("pass", "double_check_e2e", workspace, suite, errors, warnings, evidence,
                  None, "write_final_report")


def gate_final_delivery(workspace, test_suite, cfg, state, trace_ctx, events):
    errors, warnings, evidence = [], [], []

    # must pass primary_e2e first (inline check)
    suite = test_suite or "primary_e2e"
    prec_json = f"reports/test_results/{suite}_precision.json"
    if not os.path.isfile(os.path.join(workspace, prec_json)):
        errors.append(err("missing_artifact", prec_json, "primary_e2e precision result missing"))
    else:
        try:
            prec_data = json.load(open(os.path.join(workspace, prec_json)))
            if prec_data.get("status") != "pass":
                errors.append(err("precision_fail", prec_json, "primary_e2e precision not pass"))
            else:
                evidence.append(prec_json)
        except Exception as e:
            errors.append(err("parse_error", prec_json, str(e)))

    # double_check: if not_requested, skip
    dc_status = cfg.get("benchmarks", {}).get("double_check_e2e", {}).get("status", "not_requested")
    if dc_status not in ("not_requested", "skipped"):
        dc_prec = "reports/test_results/double_check_e2e_precision.json"
        if not os.path.isfile(os.path.join(workspace, dc_prec)):
            errors.append(err("missing_artifact", dc_prec, "double_check precision result missing"))
        else:
            evidence.append(dc_prec)

    # final report
    final_report = None
    for candidate in ("reports/final_report.md", "reports/final_optimization_summary.md"):
        if os.path.isfile(os.path.join(workspace, candidate)):
            final_report = candidate
            evidence.append(candidate)
            break
    if not final_report:
        errors.append(err("missing_artifact", "reports/final_report.md", "final report does not exist"))
    else:
        content = open(os.path.join(workspace, final_report)).read().lower()
        if "pearson" not in content and "precision" not in content and "jaccard" not in content:
            warnings.append("final report does not appear to reference precision evidence")
        if "speedup" not in content and "speed" not in content and "time" not in content:
            warnings.append("final report does not appear to reference runtime/speed evidence")

    # final_report_written event
    fr_events = [e for e in events if e.get("event_type") == "final_report_written" and e.get("status") == "pass"]
    if not fr_events:
        warnings.append("no final_report_written pass event in events.jsonl")
    else:
        evidence.append("logs/events.jsonl")

    if errors:
        next_agent = "bio-gpu-doc-writer-agent" if not final_report else "bio-gpu-trace-analyst-agent"
        return result("fail", "final_delivery", workspace, test_suite, errors, warnings, evidence,
                      next_agent, "write_final_report")
    return result("pass", "final_delivery", workspace, test_suite, errors, warnings, evidence,
                  None, "done")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Check workflow completion gate")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--gate", required=True, choices=sorted(VALID_GATES))
    parser.add_argument("--test-suite", dest="test_suite", default=None)
    args = parser.parse_args()

    ws = args.workspace
    gate = args.gate

    # pre-checks
    pre_errors = pre_checks(ws)
    if pre_errors:
        out = result("fail", gate, ws, args.test_suite, pre_errors, [], [],
                     "bio-gpu-trace-analyst-agent", None)
        print(json.dumps(out, indent=2))
        run_log_event(ws, gate, "fail", f"Completion gate pre-check failed: {gate}")
        sys.exit(1)

    try:
        import yaml
        cfg = load_yaml_cfg(ws)
        state = load_task_state(ws)
        trace_ctx = load_trace_ctx(ws)
        events = load_events(ws)
    except Exception as e:
        out = {"status": "error", "gate": gate, "errors": [str(e)]}
        print(json.dumps(out, indent=2))
        sys.exit(2)

    if gate == "project_init":
        out = gate_project_init(ws, args.test_suite, cfg, state, trace_ctx)
    elif gate == "test_plan":
        out = gate_test_plan(ws, args.test_suite, cfg, state, trace_ctx)
    elif gate == "primary_e2e":
        out = gate_primary_e2e(ws, args.test_suite, cfg, state, trace_ctx, events)
    elif gate == "double_check_e2e":
        out = gate_double_check_e2e(ws, args.test_suite, cfg, state, trace_ctx, events)
    elif gate == "final_delivery":
        out = gate_final_delivery(ws, args.test_suite, cfg, state, trace_ctx, events)
    else:
        out = {"status": "error", "gate": gate, "errors": [f"unknown gate: {gate}"]}
        print(json.dumps(out, indent=2))
        sys.exit(2)

    print(json.dumps(out, indent=2))

    status = out.get("status", "fail")
    run_log_event(ws, gate, status if status != "skipped" else "pass",
                  f"Completion gate checked: {gate} → {status}")
    sys.exit(0 if status in ("pass", "skipped") else 1)


if __name__ == "__main__":
    main()
