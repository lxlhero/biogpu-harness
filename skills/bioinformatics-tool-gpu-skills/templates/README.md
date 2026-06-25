# BioGPU Templates

This directory contains reusable report and script templates for BioGPU-Harness agents.

Templates are **formatting references**, not runtime artifacts.

Actual project outputs must be written to:

```
transfer2gpu/<tool>/reports/
transfer2gpu/<tool>/runs/
transfer2gpu/<tool>/artifacts/
```

## Active Templates

| Template | Purpose | Primary Consumer |
|----------|---------|------------------|
| `feasibility_report.md` | GPU feasibility report format（bottleneck evidence, Amdahl ceiling, go/no-go）| bio-gpu-feasibility-agent |
| `benchmark_report.md` | Module-level benchmark design report format | bio-gpu-benchmark-agent |
| `e2e_comparison_report.md` | Full CPU vs GPU E2E comparison report format | bio-gpu-test-runner-agent |
| `user_benchmark_report.md` | double_check_e2e user benchmark report format | bio-gpu-test-runner-agent |
| `final_optimization_summary.md` | Final delivery summary report format | bio-gpu-doc-writer-agent |

## Candidate Templates

Scripts in this directory are format references. They may be moved to `scripts/templates/` in a future phase.

| Template | Note |
|----------|------|
| `benchmark_real_data.py` | Benchmark data preparation script template |
| `e2e_checkpoint.sh` | Checkpoint-based E2E pipeline script template |

## Rules

- Templates define report structure and field names only.
- Agents use templates as formatting guides when generating reports.
- Do not write runtime execution results into templates.
- When adding a new template, add a row to the Active Templates table above.
