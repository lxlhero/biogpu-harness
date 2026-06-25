# Bottleneck Analysis Framework

## Purpose

Identify the true runtime bottleneck before any GPU work begins. Misidentifying the bottleneck is the primary cause of GPU projects that produce negligible E2E speedup.

## Bottleneck Types

**CPU compute bottleneck** — matrix multiplications, nested loops over large arrays, eigendecomposition. This is the primary good GPU candidate. Verify the operation is genuinely compute-bound before proceeding.

**I/O bottleneck** — file reads, PLINK/BGEN parsing, CSV loading, database queries. NOT a GPU candidate. Optimize with faster I/O libraries, caching, or parallel file reads instead.

**Python orchestration overhead** — a Python loop calling small operations one at a time. The fix is vectorization on CPU first, not GPU. GPU-ifying a Python loop without batching the operations gains nothing.

**Memory bandwidth bottleneck** — reading/writing large arrays without reuse. Check if data can be restructured for better cache locality. GPU may help if the GPU has higher memory bandwidth, but verify.

**CPU/GPU transfer bottleneck** — if data transfer across PCIe dominates measured time, GPU speedup is illusory. Profile transfer time explicitly with `torch.cuda.synchronize()` around transfers.

**Poor batching** — N serial GPU calls instead of 1 batched call. Each kernel launch has overhead (~5–50 µs). Calling a kernel N=5000 times serially loses most of the GPU advantage.

**Sparse or irregular access patterns** — scatter/gather operations, variable-length lookups, data-dependent branching. These map poorly to GPU and often run slower than CPU.

## Amdahl's Law Ceiling Check

Before writing any GPU code, compute the E2E speedup ceiling:

```
Max E2E speedup = 1 / (1 - F + F/S)
```

Where:
- `F` = fraction of total runtime spent in the target step (measured, not estimated)
- `S` = GPU speedup of that step (optimistic estimate)

**Key thresholds:**
- If F < 0.15, E2E ceiling is below 1.2x regardless of kernel speedup.
- If F = 0.04, even a 100x kernel speedup yields only 1.04x E2E.
- Minimum useful target: F > 0.30 before GPU work is justified.

**Example:** Target step is 4% of total runtime. GPU kernel is 100x faster on that step.

```
Max speedup = 1 / (1 - 0.04 + 0.04/100) = 1 / 0.9604 ≈ 1.04x
```

This project should not proceed with GPU-ification of that step.

## "Why Only 5% Speedup?" Diagnostic

When GPU work produces unexpectedly small E2E gains, check in order:

1. Measure F precisely — the target step may be a smaller fraction than assumed.
2. Check if a different step grew to dominate after the GPU step was accelerated.
3. Check CPU/GPU transfer time — synchronize before timing both sides.
4. Check for serial Python orchestration around the GPU call.
5. Recompute Amdahl's ceiling — if ceiling is 1.06x, 1.05x is the expected result, not a bug.

Fix the TRUE bottleneck. If F is small, improve parallelism, algorithmic complexity, or I/O throughput in the dominant step rather than optimizing the already-fast GPU step.

## Profiling Tools

- `cProfile` — function-level CPU profiling
- `py-spy` — sampling profiler, low overhead, works on running processes
- `line_profiler` — line-level timing for a specific function
- `torch.profiler` — GPU kernel timing, memory, and CPU/GPU overlap
