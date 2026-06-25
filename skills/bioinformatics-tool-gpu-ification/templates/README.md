# Templates

Report templates for GPU-ification deliverables. These are fill-in-the-blank documents — not execution instructions.

## Files

| File | Purpose |
|------|---------|
| `feasibility_report.md` | Feasibility analysis: bottleneck evidence, GPU suitability, Amdahl ceiling, go/no-go |
| `benchmark_report.md` | Module-level benchmark: environment, commands, results, speedup, accuracy |
| `e2e_comparison_report.md` | Full CPU vs GPU pipeline comparison with per-step output diff and verdict |
| `user_benchmark_report.md` | User-provided benchmark with explicit non-duplication check |
| `final_optimization_summary.md` | Delivery summary: what was optimized, results, accuracy, artifact, limitations |
| `e2e_checkpoint.sh` | Reusable checkpoint-based pipeline script for H200 jobs |
| `benchmark_real_data.py` | Helper script for real-data benchmark preparation |
