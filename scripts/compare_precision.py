#!/usr/bin/env python3
"""Generic precision metric executor for CPU vs GPU output comparison."""

import argparse
import csv
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.schema_utils import load_schema, validate_against_schema

try:
    import yaml
    from scipy import stats
    import numpy as np
except ImportError as e:
    print(json.dumps({"status": "error", "reason": "missing_dependency", "metrics": [], "failed_metrics": [], "errors": [str(e)]}))
    sys.exit(2)

VALID_METRICS = {
    "pearson", "spearman", "rmse", "mae", "max_abs_error", "relative_error",
    "jaccard", "f1", "exact_match", "row_count_match", "file_exists", "ratio",
}


# ── file loading ──────────────────────────────────────────────────────────────

def _detect_sep(path):
    with open(path) as f:
        first = f.readline()
    return "\t" if "\t" in first else ","


def load_column(path, value_column, key_column=None):
    sep = _detect_sep(path)
    with open(path, newline="") as f:
        reader = csv.DictReader(f, delimiter=sep)
        rows = list(reader)
    if key_column:
        return {r[key_column]: float(r[value_column]) for r in rows}
    return [float(r[value_column]) for r in rows]


def load_set(path, key_column):
    sep = _detect_sep(path)
    with open(path, newline="") as f:
        reader = csv.DictReader(f, delimiter=sep)
        return {r[key_column] for r in reader}


def align_by_key(cpu_map, gpu_map):
    keys = sorted(set(cpu_map) & set(gpu_map))
    return [cpu_map[k] for k in keys], [gpu_map[k] for k in keys]


def row_count(path):
    sep = _detect_sep(path)
    with open(path, newline="") as f:
        reader = csv.DictReader(f, delimiter=sep)
        return sum(1 for _ in reader)


def resolve(path, workspace):
    if os.path.isabs(path):
        return path
    return os.path.join(workspace, path)


# ── metric runners ────────────────────────────────────────────────────────────

def run_metric(cfg, workspace):
    name = cfg["name"]
    result = {"name": name, "threshold": cfg.get("threshold"), "direction": cfg.get("direction"), "status": None}

    try:
        if name in ("pearson", "spearman"):
            cpu_p = resolve(cfg["cpu_file"], workspace)
            gpu_p = resolve(cfg["gpu_file"], workspace)
            vc = cfg["value_column"]
            kc = cfg.get("key_column")
            if kc:
                cpu_d = load_column(cpu_p, vc, kc)
                gpu_d = load_column(gpu_p, vc, kc)
                cpu_v, gpu_v = align_by_key(cpu_d, gpu_d)
            else:
                cpu_v = load_column(cpu_p, vc)
                gpu_v = load_column(gpu_p, vc)
            if name == "pearson":
                val, _ = stats.pearsonr(cpu_v, gpu_v)
            else:
                val, _ = stats.spearmanr(cpu_v, gpu_v)
            result.update({"value": round(val, 6), "cpu_file": cfg["cpu_file"], "gpu_file": cfg["gpu_file"]})

        elif name in ("rmse", "mae", "max_abs_error", "relative_error"):
            cpu_p = resolve(cfg["cpu_file"], workspace)
            gpu_p = resolve(cfg["gpu_file"], workspace)
            vc = cfg["value_column"]
            kc = cfg.get("key_column")
            if kc:
                cpu_d = load_column(cpu_p, vc, kc)
                gpu_d = load_column(gpu_p, vc, kc)
                cpu_v, gpu_v = align_by_key(cpu_d, gpu_d)
            else:
                cpu_v = load_column(cpu_p, vc)
                gpu_v = load_column(gpu_p, vc)
            diffs = [g - c for c, g in zip(cpu_v, gpu_v)]
            if name == "rmse":
                val = math.sqrt(sum(d**2 for d in diffs) / len(diffs))
            elif name == "mae":
                val = sum(abs(d) for d in diffs) / len(diffs)
            elif name == "max_abs_error":
                val = max(abs(d) for d in diffs)
            else:  # relative_error
                val = max(abs((g - c) / c) for c, g in zip(cpu_v, gpu_v) if c != 0)
            result.update({"value": round(val, 6), "cpu_file": cfg["cpu_file"], "gpu_file": cfg["gpu_file"]})

        elif name == "jaccard":
            cpu_s = load_set(resolve(cfg["cpu_file"], workspace), cfg["key_column"])
            gpu_s = load_set(resolve(cfg["gpu_file"], workspace), cfg["key_column"])
            inter = len(cpu_s & gpu_s)
            union = len(cpu_s | gpu_s)
            val = inter / union if union > 0 else 1.0
            result.update({"value": round(val, 6), "cpu_file": cfg["cpu_file"], "gpu_file": cfg["gpu_file"]})

        elif name == "f1":
            cpu_p = resolve(cfg["cpu_file"], workspace)
            gpu_p = resolve(cfg["gpu_file"], workspace)
            lc = cfg["label_column"]
            kc = cfg.get("key_column")
            sep_c, sep_g = _detect_sep(cpu_p), _detect_sep(gpu_p)
            with open(cpu_p, newline="") as f:
                cpu_rows = {r.get(kc, str(i)): r[lc] for i, r in enumerate(csv.DictReader(f, delimiter=sep_c))}
            with open(gpu_p, newline="") as f:
                gpu_rows = {r.get(kc, str(i)): r[lc] for i, r in enumerate(csv.DictReader(f, delimiter=sep_g))}
            keys = sorted(set(cpu_rows) & set(gpu_rows))
            y_true = [cpu_rows[k] for k in keys]
            y_pred = [gpu_rows[k] for k in keys]
            labels = sorted(set(y_true) | set(y_pred))
            tp = sum(1 for t, p in zip(y_true, y_pred) if t == p and t == labels[0])
            fp = sum(1 for t, p in zip(y_true, y_pred) if t != p and p == labels[0])
            fn = sum(1 for t, p in zip(y_true, y_pred) if t != p and t == labels[0])
            prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            val = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
            result.update({"value": round(val, 6), "cpu_file": cfg["cpu_file"], "gpu_file": cfg["gpu_file"]})

        elif name == "exact_match":
            cpu_content = open(resolve(cfg["cpu_file"], workspace)).read()
            gpu_content = open(resolve(cfg["gpu_file"], workspace)).read()
            val = 1.0 if cpu_content == gpu_content else 0.0
            result.update({"value": val, "cpu_file": cfg["cpu_file"], "gpu_file": cfg["gpu_file"]})
            result["threshold"] = result.get("threshold", 1.0)
            result["direction"] = result.get("direction", ">=")

        elif name == "row_count_match":
            cpu_n = row_count(resolve(cfg["cpu_file"], workspace))
            gpu_n = row_count(resolve(cfg["gpu_file"], workspace))
            val = 1 if cpu_n == gpu_n else 0
            result.update({"value": val, "cpu_rows": cpu_n, "gpu_rows": gpu_n,
                           "cpu_file": cfg["cpu_file"], "gpu_file": cfg["gpu_file"]})
            result["threshold"] = result.get("threshold", 1)
            result["direction"] = result.get("direction", "==")

        elif name == "file_exists":
            target = cfg.get("file") or cfg.get("gpu_file")
            exists = os.path.isfile(resolve(target, workspace))
            val = 1 if exists else 0
            result.update({"value": val, "file": target})
            result["threshold"] = result.get("threshold", 1)
            result["direction"] = result.get("direction", ">=")

        elif name == "ratio":
            cpu_p = resolve(cfg["cpu_file"], workspace)
            gpu_p = resolve(cfg["gpu_file"], workspace)
            vc = cfg["value_column"]
            kc = cfg.get("key_column")
            if kc:
                cpu_d = load_column(cpu_p, vc, kc)
                gpu_d = load_column(gpu_p, vc, kc)
                cpu_v, gpu_v = align_by_key(cpu_d, gpu_d)
            else:
                cpu_v = load_column(cpu_p, vc)
                gpu_v = load_column(gpu_p, vc)
            ratios = [g / c for c, g in zip(cpu_v, gpu_v) if c != 0]
            lo = cfg["threshold_low"]
            hi = cfg["threshold_high"]
            in_range = [lo <= r <= hi for r in ratios]
            val = round(min(ratios), 6) if ratios else None
            result.update({
                "value": val,
                "ratio_min": round(min(ratios), 6) if ratios else None,
                "ratio_max": round(max(ratios), 6) if ratios else None,
                "threshold_low": lo, "threshold_high": hi,
                "cpu_file": cfg["cpu_file"], "gpu_file": cfg["gpu_file"],
            })
            result["status"] = "pass" if all(in_range) else "fail"
            return result

        else:
            result["status"] = "error"
            result["error"] = f"unsupported metric: {name}"
            return result

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        return result

    # evaluate direction for non-ratio metrics
    threshold = result.get("threshold")
    direction = result.get("direction", ">=")
    val = result.get("value")
    if threshold is not None and val is not None:
        if direction == "==":
            passed = val == threshold
        elif direction == ">=":
            passed = val >= threshold
        elif direction == "<=":
            passed = val <= threshold
        elif direction == ">":
            passed = val > threshold
        elif direction == "<":
            passed = val < threshold
        else:
            passed = False
        result["status"] = "pass" if passed else "fail"
    else:
        result["status"] = "pass"

    return result


# ── test plan parsing ─────────────────────────────────────────────────────────

def extract_precision_config(md_path):
    text = open(md_path).read()
    # find yaml code block containing precision_config:
    pattern = r"```yaml\s*(precision_config:.*?)```"
    m = re.search(pattern, text, re.DOTALL)
    if not m:
        return None
    return yaml.safe_load(m.group(1))


# ── report writing ────────────────────────────────────────────────────────────

def write_markdown(results, test_suite, out_md):
    overall = "PASS" if all(r["status"] == "pass" for r in results) else "FAIL"
    rows = []
    for r in results:
        val = r.get("value")
        val_str = f"{val:.6f}" if isinstance(val, float) else str(val)
        thr = r.get("threshold") or r.get("threshold_low", "")
        if r.get("threshold_high") is not None:
            thr = f"[{r['threshold_low']}, {r['threshold_high']}]"
        direction = r.get("direction", ">=")
        rows.append(f"| {r['name']} | {val_str} | {thr} | {direction} | {r['status'].upper()} |")

    cpu_files = sorted({r["cpu_file"] for r in results if "cpu_file" in r})
    gpu_files = sorted({r["gpu_file"] for r in results if "gpu_file" in r})
    inputs = "\n".join(f"- CPU: {f}" for f in cpu_files) + "\n" + "\n".join(f"- GPU: {f}" for f in gpu_files)

    md = f"""# Precision Comparison Report

## Summary

Status: {overall}
Test Suite: {test_suite}

## Metrics

| Metric | Value | Threshold | Direction | Status |
|---|---:|---:|---|---|
{chr(10).join(rows)}

## Inputs

{inputs}
"""
    os.makedirs(os.path.dirname(out_md), exist_ok=True)
    with open(out_md, "w") as f:
        f.write(md)


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Compare CPU vs GPU output precision")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--test-plan", dest="test_plan", default=None)
    parser.add_argument("--out-json", dest="out_json", required=True)
    parser.add_argument("--out-md", dest="out_md", required=True)
    # explicit mode
    parser.add_argument("--cpu-output", dest="cpu_output", default=None)
    parser.add_argument("--gpu-output", dest="gpu_output", default=None)
    parser.add_argument("--metric", default=None)
    parser.add_argument("--key-column", dest="key_column", default=None)
    parser.add_argument("--value-column", dest="value_column", default=None)
    parser.add_argument("--threshold", type=float, default=None)
    parser.add_argument("--direction", default=">=")
    args = parser.parse_args()

    # get precision config
    if args.test_plan:
        cfg_root = extract_precision_config(args.test_plan)
        if cfg_root is None:
            out = {"status": "error", "reason": "missing_precision_config", "metrics": [], "failed_metrics": [],
                   "errors": ["test_plan does not contain precision_config"]}
            print(json.dumps(out, indent=2))
            sys.exit(2)

        # ── schema validation ─────────────────────────────────────────────────
        try:
            schema = load_schema("precision_config.schema.json")
            schema_errs = validate_against_schema(cfg_root, schema)
        except Exception as e:
            schema_errs = [{"path": "(schema)", "message": str(e)}]

        if schema_errs:
            out = {"status": "error", "reason": "schema_fail",
                   "schema_errors": schema_errs, "metrics": [], "failed_metrics": [],
                   "errors": [e["message"] for e in schema_errs]}
            print(json.dumps(out, indent=2))
            sys.exit(2)

        pc = cfg_root.get("precision_config", cfg_root)
        test_suite = pc.get("test_suite", "unknown")
        metrics_cfg = pc.get("metrics", [])
    elif args.metric:
        test_suite = "explicit"
        metrics_cfg = [{
            "name": args.metric,
            "cpu_file": args.cpu_output,
            "gpu_file": args.gpu_output,
            "key_column": args.key_column,
            "value_column": args.value_column,
            "threshold": args.threshold,
            "direction": args.direction,
        }]
    else:
        out = {"status": "error", "reason": "no_input", "metrics": [], "failed_metrics": [],
               "errors": ["provide --test-plan or --metric"]}
        print(json.dumps(out, indent=2))
        sys.exit(2)

    if not metrics_cfg:
        out = {"status": "error", "reason": "no_metrics", "metrics": [], "failed_metrics": [],
               "errors": ["precision_config.metrics is empty"]}
        print(json.dumps(out, indent=2))
        sys.exit(2)

    results = [run_metric(cfg, args.workspace) for cfg in metrics_cfg]

    failed = [r["name"] for r in results if r["status"] != "pass"]
    errors = [f"{r['name']}: {r.get('error', '')}" for r in results if r["status"] == "error"]
    overall = "pass" if not failed else "fail"

    out = {
        "status": overall,
        "test_suite": test_suite,
        "metrics": results,
        "failed_metrics": failed,
        "errors": errors,
    }

    os.makedirs(os.path.dirname(args.out_json), exist_ok=True)
    with open(args.out_json, "w") as f:
        json.dump(out, f, indent=2)

    write_markdown(results, test_suite, args.out_md)

    print(json.dumps(out, indent=2))
    sys.exit(0 if overall == "pass" else 1)


if __name__ == "__main__":
    main()
