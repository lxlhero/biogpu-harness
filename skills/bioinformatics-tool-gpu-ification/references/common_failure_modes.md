# Common Failure Modes in GPU-Ification of Bioinformatics Tools

---

## Kernel speedup does not translate to E2E speedup

**Symptom:** Kernel shows 10x speedup, but pipeline runs only 5% faster end-to-end.
**Root cause:** The GPU-accelerated step is a small fraction of total runtime (Amdahl's Law).
**Detection:** Profile E2E; check what % of runtime the target step actually is.
**Mitigation:** First reduce the dominant bottleneck (parallelize, optimize I/O, algorithmic improvement). Then re-evaluate GPU acceleration.

---

## GPU-ification attempted without profiling

**Symptom:** GPU version is slower or barely faster than CPU.
**Root cause:** The assumed hotspot was not actually the bottleneck.
**Detection:** Run cProfile / py-spy / line_profiler on the CPU pipeline.
**Mitigation:** Always profile before writing any GPU code.

---

## Per-element CUDA calls instead of vectorized batch

**Symptom:** N GPU calls in a Python loop. 690x slower than expected.
**Root cause:** Each CUDA call has kernel launch overhead (~0.1ms). N=5000 calls = 500ms overhead even before computation.
**Detection:** Python loop with individual torch operations on each sample/spot.
**Mitigation:** Vectorize: stack inputs, call one batched operation over all samples at once.

---

## Small input: kernel launch overhead dominates

**Symptom:** GPU is 5-10x slower than CPU for small datasets.
**Root cause:** CUDA kernel launch overhead dominates for inputs < ~10K elements.
**Detection:** Benchmark at multiple scales; slowdown only at small scale.
**Mitigation:** Keep small inputs on CPU; GPU only for large inputs. Or use device toggle.

---

## No E2E validation against the original tool

**Symptom:** GPU version "works" but results not validated against the real tool.
**Root cause:** Comparison was against a self-written CPU mirror, not the original tool.
**Detection:** Check if comparison baseline is the actual CRAN package / official CLI.
**Mitigation:** Always run the original tool in the same rjob and compare outputs directly.

---

## Mirror implementation used as precision reference

**Symptom:** GPU precision appears good, but on real data results differ.
**Root cause:** A self-written CPU reimplementation was used as reference instead of the original. Both may share the same bug.
**Detection:** If the reference is not the official/original tool, it is a mirror.
**Mitigation:** Run the actual original tool's CLI. Save its output. Use that as the gold standard.

---

## Runtime string-replace patch breaks indentation

**Symptom:** `IndentationError` or `SyntaxError` at import time after Docker build.
**Root cause:** Runtime string replacement for code injection mismatches indentation of class methods (4-space offset).
**Detection:** `ast.parse(open("patched_file.py").read())` fails before build.
**Mitigation:** Pre-patch the file locally, validate with `ast.parse()`, then `COPY` the verified file in Dockerfile. Never use runtime string replacement for code injection.

---

## Three-layer integration verification skipped before image build

**Symptom:** Bug discovered only after Docker build + rjob cycle (15+ min wasted per bug).
**Root cause:** Code was pushed to Docker without passing: (1) syntax check, (2) symbol/import check, (3) semantic check.
**Detection:** Missing any of: `ast.parse()`, `python3 -c "import module"`, synthetic data functional test.
**Mitigation:** Mandatory three layers before any image build: Syntax → Symbol → Semantic.

---

## Amdahl's Law ceiling not computed

**Symptom:** Significant engineering effort invested in GPU kernel that gives <5% E2E speedup.
**Root cause:** Speedup potential was not evaluated before implementation.
**Detection:** Compute `1 / (1 - F + F/S)` where F = step's fraction of total runtime.
**Mitigation:** If ceiling < 1.15x, stop. Address the actual bottleneck instead.

---

## Sentinel files block parallel execution

**Symptom:** Per-unit parallel jobs (e.g., per-chromosome) fail or produce partial results.
**Root cause:** A global `.done` sentinel file designed for serial execution is touched by individual workers.
**Detection:** Each parallel unit touches a shared completion marker.
**Mitigation:** Individual workers must not touch the global sentinel. Only the orchestrator wrapper marks completion after all subprocesses succeed.

---

## Match mathematical equivalence but not numerical path

**Symptom:** GPU output is very close (Pearson 0.999) but fails the 0.9999 threshold.
**Root cause:** Two mathematically equivalent expressions produce different floating-point results due to different rounding in intermediate steps. Example: `Xty - X^T @ (X @ b)` (double round-trip) vs `Xty - XtX @ b` (single mv with precomputed Gram matrix).
**Detection:** Results diverge slightly and drift over iterations. Compare the BLAS call sequence of the original source code to the GPU port.
**Mitigation:** Read the original source code and replicate the EXACT sequence of matrix operations, not just the mathematical formula.

---

## Diagonal trace approximation breaks on real correlated data

**Symptom:** sigma² systematically 20-70% too high on real genomic data, but correct on synthetic data.
**Root cause:** Variational Bayes sigma² update uses `tr(XᵀX · Cov(b))`. Diagonal approximation is exact only when XᵀX is diagonal, which holds for synthetic i.i.d. data but NOT for real LD-correlated data.
**Detection:** Synthetic data passes all thresholds; real data fails only on sigma².
**Mitigation:** Compute the full quadratic form: `Σⱼ dⱼ·Σₗ αₗⱼ·µ₂ₗⱼ − Σₗ B[l]ᵀ·XtX·B[l]`.

---

## GPU debug phase used synthetic data only

**Symptom:** All tests pass during development, then fail immediately on real data.
**Root cause:** Synthetic Gaussian data hides LD structure and correlated-covariate bugs. Bugs only manifest on real genomic/biological data.
**Detection:** If benchmark data was generated by `np.random`, `rnorm`, or similar — it is synthetic.
**Mitigation:** `prepare_benchmark.R/py` with real public data (1000G, GTEx, etc.) must be ready BEFORE any GPU code is written. First debug rjob must use real data.

---

## Standardize parameter mismatch between CPU and GPU paths

**Symptom:** Medium/large-scale real data shows PIP divergence; small datasets pass.
**Root cause:** R functions like `susieR::susie()` default to `standardize=TRUE`, which transforms input before the algorithm. GPU replacement assumes pre-standardized input. CPU path standardizes internally, GPU path doesn't → different effective inputs.
**Detection:** Per-component alpha correlation ~0.90 but mu2 correlation >0.999; divergence amplifies through softmax.
**Mitigation:** Set `standardize=FALSE` in the CPU path to match GPU. Audit ALL default parameters of the original function that silently transform input data.

---

## Permutation-based methods validated with insufficient permutations

**Symptom:** GPU vs CPU Jaccard ≈ 0.57, appears to be a bug.
**Root cause:** 100 permutations is insufficient — CPU-vs-CPU Jaccard ≈ 0.59 at 100 perm due to sampling variance. This is normal, not a bug.
**Detection:** Test run with 100 permutations.
**Mitigation:** Use ≥1000 permutations for precision validation. Jaccard > 0.80 at 1000 perm is PASS.
