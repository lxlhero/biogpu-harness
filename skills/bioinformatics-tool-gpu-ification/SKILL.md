---
name: bioinformatics-tool-gpu-ification
description: "Reusable methodology, validation principles, benchmark design, report templates, and reference materials for GPU acceleration of bioinformatics tools."
---

# Bioinformatics Tool GPU-ification Skill

## Purpose

This skill provides reusable methodology, principles, validation guidance, benchmark design guidance, report templates, and reference materials for GPU acceleration of bioinformatics tools.

It is a **methodology and resource layer**, not an executable agent workflow.

## Scope

Use this skill for bioinformatics GPU acceleration tasks involving:

- Matrix-heavy computation (scoring, regression, factorization)
- Gene or cell scoring pipelines
- Embedding generation and similarity search
- Ranking and top-k selection
- Sparse/dense data transformation
- Batch processing over many samples or traits
- CPU/GPU hybrid pipelines
- End-to-end scientific workflow acceleration
- R tools calling GPU kernels via reticulate

## Non-goals

This skill does not define:

- The `/gpu-team` execution workflow or agent dispatch order
- Step transitions, failure recovery, or rjob execution parameters
- Docker image build procedures or E2E tester hard rules
- Project-specific delivery history (gsMap, susieR, SCAVENGE versions)
- Tool-specific bug records

Those belong to `.claude/commands`, `.claude/knowledge`, or `archive/`.

## Relationship to gpu-team Commands

The executable workflow is maintained in `.claude/commands/gpu-team.md` and related `.claude/commands/gpu-*.md` files.

When execution order, agent responsibility, stage transition, or mandatory validation behavior is involved, **commands are the source of truth**.

This skill is used for methodology, validation philosophy, benchmark principles, and reusable templates.

## Relationship to .claude/knowledge

The `.claude/knowledge` directory contains project-level shared knowledge used directly by the current gpu-team commands at runtime.

This skill contains reusable, cross-project methodology.

Do not maintain duplicate pitfall systems in both places.

## Core Principles

- Identify the bottleneck before writing any GPU code.
- Compute the Amdahl's Law ceiling before investing in GPU-ification.
- Establish a reliable CPU baseline before optimization.
- Validate correctness against the original tool before measuring speed.
- Prefer E2E speedup over isolated kernel speedup.
- Avoid GPU acceleration when I/O, orchestration, or transfer overhead dominates.
- Use real biological data for correctness validation; synthetic data only for smoke tests.
- Tie accuracy validation to the tool's final user-facing outputs.
- Document baseline, GPU results, accuracy, speed, environment, and limitations.
- Do not preserve project-specific bug history in this skill.

## Methodology References

- [`references/gpu_porting_principles.md`](references/gpu_porting_principles.md) — core GPU porting philosophy
- [`references/bottleneck_analysis.md`](references/bottleneck_analysis.md) — bottleneck identification framework
- [`references/gpu_suitability.md`](references/gpu_suitability.md) — GPU suitability decision guide
- [`references/benchmark_design.md`](references/benchmark_design.md) — benchmark tiers, real-data requirements, user benchmark protocol
- [`references/validation_metrics.md`](references/validation_metrics.md) — accuracy thresholds per output type
- [`references/performance_metrics.md`](references/performance_metrics.md) — E2E vs kernel speedup measurement
- [`references/common_failure_modes.md`](references/common_failure_modes.md) — 15 common GPU-ification failure modes
- [`references/bioinformatics_gpu_patterns.md`](references/bioinformatics_gpu_patterns.md) — reusable GPU code patterns for bioinformatics

## Templates

- [`templates/feasibility_report.md`](templates/feasibility_report.md) — feasibility analysis and go/no-go decision
- [`templates/benchmark_report.md`](templates/benchmark_report.md) — module-level benchmark results
- [`templates/e2e_comparison_report.md`](templates/e2e_comparison_report.md) — full CPU vs GPU pipeline comparison
- [`templates/user_benchmark_report.md`](templates/user_benchmark_report.md) — user-provided benchmark validation
- [`templates/final_optimization_summary.md`](templates/final_optimization_summary.md) — delivery summary

## Archive

Historical project delivery notes and tool-specific records from completed projects are not part of this skill. They are kept in each project's own directory under `transfer2gpu/`.
