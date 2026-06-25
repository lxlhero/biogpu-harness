# Validation Metrics for GPU-Accelerated Bioinformatics Outputs

## Output Type → Metric Mapping

| Output type | Metric | Threshold |
|-------------|--------|-----------|
| Continuous scores (PIP, LD score, beta, embedding) | Pearson r | > 0.99 |
| p-values | Pearson r | > 0.999 |
| Variance parameters (sigma², h²) | ratio | ∈ (0.99, 1.01) |
| Credible/significant sets (CS, QTL) | Jaccard | > 0.95 (deterministic) |
| Permutation-based significant sets | Jaccard | > 0.80 (≥1000 perm required) |
| Binary classification | F1 | > 0.95 |
| Rankings / top-k | Spearman correlation or top-k overlap | task-specific |

---

## Jaccard Threshold Nuance

Jaccard > 0.95 applies ONLY to deterministic algorithms.

For permutation-based methods (e.g., randomWalk permutation tests):
- 100 permutations: CPU-vs-CPU Jaccard ≈ 0.59 — this is sampling variance, not a bug
- 1000 permutations: Jaccard > 0.80 is PASS
- Never judge precision from 100-perm runs

---

## ELBO Equivalence for Non-Convex Methods

For variational Bayes methods (SuSiE, etc.) on real LD-correlated data:
- GPU and CPU may converge to different local optima
- If |ELBO_CPU - ELBO_GPU| < 1 nat: both are valid local optima — PASS
- Document as "multiple local optima due to LD structure", not precision failure
- Pearson r requirement may be relaxed when ELBO equivalence is confirmed

---

## Float Path Matching Strategy

**Tier 1 — Byte-exact (preferred):**
- Match the ORIGINAL numerical path exactly, not just mathematical equivalence
- Example: if original code uses precomputed XtX + single `mv()`, do the same — do not replace with two separate MV calls even if mathematically identical
- For float16 paths: scipy.gmean and torch log differ at bit level (~8e-4) — do the log step on CPU via numpy for byte-exact match

**Tier 2 — Document divergence (fallback):**
- Confirm Pearson threshold still met
- Show max diff is within IEEE 754 bounds
- Explicitly state it is float precision, not algorithmic error

---

## Reference

For float path matching details, see `gpu-precision-matching.md`.
