# BioGPU References

This directory contains long-form methodology references for BioGPU-Harness agents.

These files are **not loaded by default**.
Agents read them **on demand** when the runtime knowledge digest is insufficient.

## References

| File | Purpose | Primary Consumers |
|------|---------|-------------------|
| `benchmark_design.md` | Benchmark selection and design methodology（分层、真实数据要求、用户 benchmark 协议）| bio-gpu-benchmark-agent, bio-gpu-test-planner-agent |
| `bioinformatics_gpu_patterns.md` | Common GPU acceleration patterns for bioinformatics workloads（详版代码模式）| bio-gpu-feasibility-agent, bio-gpu-code-planner-agent |
| `bottleneck_analysis.md` | Deep bottleneck analysis methods（Amdahl 详版、profiling 框架）| bio-gpu-profiling-agent, bio-gpu-existing-project-planner-agent |
| `common_failure_modes.md` | Long-form failure taxonomy（15 种失败模式，含诊断和缓解）| bio-gpu-problem-analyst-agent, bio-gpu-code-reviewer-agent |
| `elbo-diagnostic-softmax.md` | ELBO softmax diagnostic method | domain-specific, on demand |
| `gpu-precision-matching.md` | Precision matching between CPU/GPU implementations | bio-gpu-test-planner-agent, bio-gpu-module-tester-agent |
| `gpu_porting_principles.md` | General GPU porting philosophy and decision criteria | bio-gpu-feasibility-agent, bio-gpu-code-planner-agent |
| `gpu_suitability.md` | GPU suitability assessment guide | bio-gpu-feasibility-agent |
| `performance_metrics.md` | Speedup and performance metric definitions（E2E vs kernel）| bio-gpu-benchmark-agent, bio-gpu-test-runner-agent |
| `sigma2-trace-correction.md` | Sigma² trace correction method（variational Bayes）| domain-specific, on demand |
| `validation_metrics.md` | Validation metric selection per output type | bio-gpu-test-planner-agent |

## Rules

- This list reflects **only files that actually exist** in this directory.
- Do not add entries for files that do not exist.
- When adding a new reference, update this README with file, purpose, and primary consumers.
