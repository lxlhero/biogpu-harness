---
name: bioinformatics-tool-gpu-skills
description: "Long-form methodology, benchmark design, validation principles, GPU patterns, and report templates for GPU acceleration of bioinformatics tools."
---

# Bioinformatics Tool GPU Skills

This directory is the **long-form methodology and template asset library** for BioGPU-Harness.

It is **not** the runtime orchestrator.
It is **not** the agent workflow.
It is **not** the mandatory runtime knowledge layer.

Runtime knowledge (short rules, pitfall checklist) lives in:

```
.claude/knowledge/
```

Specialist agents live in:

```
.claude/agents/
```

User-facing commands live in:

```
.claude/commands/
```

---

## What belongs here

- Complete GPU-ification methodology
- Benchmark design and selection principles
- Bottleneck analysis detailed framework
- GPU suitability assessment guide
- Validation metrics design
- Performance metrics definitions
- Bioinformatics GPU code patterns (detailed)
- Long-form failure mode taxonomy
- Report and script templates

## What does not belong here

- `/bio-gpu-team` routing rules → `.claude/commands/`
- Current task_state or next_action state → `state/task_state.json`
- Runtime artifacts (results, logs) → `transfer2gpu/<tool>/`
- Short hard rules agents always check → `.claude/knowledge/`
- Current project paths → `biogpu_project.yaml`
- Deprecated backup files (`.bak`)

---

## Usage Policy

Agents **must not** load all references by default.

Agents should read only the specific reference needed for the current decision.

Examples:

| Decision needed | Reference to read |
|-----------------|-------------------|
| Benchmark design | `references/benchmark_design.md` |
| Precision metric selection | `references/validation_metrics.md` |
| GPU suitability assessment | `references/gpu_suitability.md` |
| Failure diagnosis deep dive | `references/common_failure_modes.md` |
| GPU code pattern selection | `references/bioinformatics_gpu_patterns.md` |
| Report generation | `templates/` |

---

## Methodology References

See [`references/README.md`](references/README.md) for the full list with Primary Consumers.

## Templates

See [`templates/README.md`](templates/README.md) for the full list with usage rules.

---

## Relationship to `.claude/knowledge/`

`knowledge/` is the **摘要提炼版** of selected references here:

- `knowledge/methodology.md` ← digest of `bottleneck_analysis.md` + `bioinformatics_gpu_patterns.md`
- `knowledge/pitfalls/common.md` ← subset of `common_failure_modes.md`

When runtime digest is insufficient, agents read the full reference here on demand.
