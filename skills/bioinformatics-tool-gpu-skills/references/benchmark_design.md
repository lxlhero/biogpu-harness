# Benchmark Design

## Benchmark Tiers

### Tier 1 — Smoke Test
- **Purpose:** Verify code does not crash.
- **Data:** Synthetic minimal data (e.g., `np.random`, `rnorm`) acceptable here ONLY.
- **Scale:** Tiny (10s of rows/cols).
- **Pass criteria:** No crash, output has expected shape.

### Tier 2 — Module Benchmark
- **Purpose:** Validate GPU module precision and speed on real data at moderate scale.
- **Data:** Real biological data (see Tier 3 for sources).
- **Scale:** Representative of typical production workloads.
- **Pass criteria:** Accuracy metric passes threshold; module speedup measured.

### Tier 3 — Real-Dataset (E2E) Benchmark
- **Purpose:** Full end-to-end validation against original tool.
- **Data:** Real public biological data (1000 Genomes, GTEx, UK Biobank, etc.).
- **Scale:** Production-scale or close to it.
- **Pass criteria:** All output accuracy thresholds met; E2E speedup ≥ 1.15x.

### Tier 4 — User-Provided Benchmark
- **Purpose:** Validate on the user's own data or a distinct public dataset.
- **Rules:**
  - Must differ from the dataset used in Tier 3 E2E benchmark.
  - Before asking the user to provide a benchmark, declare which datasets were already used.
  - May be an open-source benchmark as long as it is not the same as the Tier 3 dataset.
- **Pass criteria:** Same accuracy thresholds as Tier 3.

### Tier 5 — Stress / Scaling Benchmark
- **Purpose:** Measure behavior at GPU VRAM limits and large scale.
- **Data:** Large public data or tiled real data.
- **Pass criteria:** No OOM, graceful chunking fallback if needed; scaling trend documented.

### Tier 6 — Regression Benchmark
- **Purpose:** Confirm a fix did not break previously passing precision or speed.
- **Data:** Same dataset as a prior benchmark.
- **Pass criteria:** Results match prior benchmark within tolerance.

---

## Required Benchmark Record Fields

Every benchmark report must include:

| Field | Required |
|-------|---------|
| Dataset name and source | Yes |
| Dataset scale (n × p or equivalent) | Yes |
| Environment (GPU model, image/tag, framework versions) | Yes |
| Baseline command (exact) | Yes |
| GPU command (exact) | Yes |
| Baseline wall-clock time | Yes |
| GPU wall-clock time | Yes |
| E2E speedup ratio | Yes |
| Module speedup (if measured separately) | If available |
| Peak GPU memory | If measurable |
| Accuracy metric(s) and threshold(s) | Yes |
| Accuracy values (CPU vs GPU) | Yes |
| Pass/Fail verdict per metric | Yes |
| Limitations (what this benchmark does not cover) | Yes |

---

## E2E vs Profiling Data Independence

The E2E benchmark dataset and the profiling/development benchmark dataset **must be independent**.

When only one dataset is available:
- Split 80/20.
- Use 80% for development/profiling, 20% for final E2E validation.
- Document the split in the benchmark report.

---

## Baseline Rules

The CPU baseline must be the **original tool** — CRAN package, official CLI, or original Python implementation.

Do NOT use:
- A self-written CPU reimplementation ("mirror CPU version")
- A modified CPU version
- An older version of the tool

Both CPU and GPU must run in the **same rjob** for fair wall-clock comparison.

---

## Real Data Requirement

Synthetic data (random matrices, simulated genotypes) is acceptable **only for Tier 1 smoke tests**.

For all other tiers, real biological data is required because:
- Synthetic data has near-diagonal covariance structure that hides real LD/correlation bugs
- Permutation test null distributions depend on real degree structures
- Float precision issues often only manifest under real data distributions

**Recommended public datasets:**
- 1000 Genomes Phase 3 VCF (genotype data, fine-mapping benchmarks)
- GTEx eQTL summary statistics
- UK Biobank fine-mapping subsets (if available)
- Official tool tutorial datasets (when publicly accessible)

---

## User Benchmark Protocol

When requesting a user-provided benchmark:

1. First state which datasets were already used in E2E validation.
2. Explain why a distinct dataset provides additional validation value.
3. Confirm the user's dataset is different from those already used.
4. If the user's dataset is the same as an already-used dataset, explain why it is not a new benchmark and suggest alternatives.

---

## Amdahl's Law Pre-Check (Before Benchmark Design)

Before designing any benchmark, compute the theoretical E2E ceiling:

```
Max E2E speedup = 1 / (1 - F + F/S)
```

where:
- F = fraction of total E2E runtime in the target step (from profiling)
- S = expected kernel-level speedup (from toy benchmark or literature)

If ceiling < 1.15x: do not invest in GPU-ification of this step.

---

## See Also

- `references/validation_metrics.md` — accuracy thresholds per output type
- `references/performance_metrics.md` — measurement methodology
- `templates/benchmark_report.md` — report template
- `templates/e2e_comparison_report.md` — E2E comparison template
- `templates/user_benchmark_report.md` — user benchmark template
