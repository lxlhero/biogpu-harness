# GPU Suitability Decision Guide

## Operations Suitable for GPU

**Large-scale matrix operations** — matrix multiply, SVD, batch matrix inversion, QR decomposition. GPU excels when matrices are large enough (typically >1000×1000) that arithmetic intensity justifies transfer cost.

**Batch scoring over many samples** — computing a score for each of N independent samples, where N is large. Embarrassingly parallel; maps directly to GPU thread model.

**Embedding generation and similarity search** — dense vector operations over large embedding tables, cosine similarity, nearest neighbor search. High arithmetic intensity, highly parallelizable.

**Sparse matrix batch operations** — `sparse.mm` over N vectors at once (batched). More efficient than N serial sparse-vector operations.

**Ranking and top-k selection over large datasets** — `torch.topk` on GPU is efficient when the input tensor is already on GPU and the operation is not a one-off.

**High arithmetic intensity operations** — when the ratio of floating-point operations to memory accesses is high, GPU compute units stay busy rather than waiting for memory.

## Operations NOT Suitable for GPU

**Small inputs (<10K elements)** — kernel launch overhead (5–50 µs) dominates actual computation time. CPU is faster for small tensors.

**I/O-bound steps** — PLINK file parsing, BGEN reading, CSV loading, database queries. The bottleneck is disk throughput, not compute. GPU cannot accelerate I/O.

**Control-flow-heavy algorithms with data-dependent branching** — GPU threads in a warp must execute the same instruction. Divergent branches serialize execution. Irregular conditionals perform poorly.

**Tasks with strong sequential dependencies** — step N depends on the result of step N−1, and the dependency chain is long. Cannot parallelize across steps; GPU advantage disappears.

**Frequent CPU/GPU round-trips** — if the algorithm alternates between CPU logic and GPU compute many times, PCIe transfer overhead accumulates. Restructure to minimize round-trips before GPU-ifying.

**Steps where surrounding orchestration is slow** — if the kernel is fast but the Python code calling it is slow (serial loops, unvectorized preprocessing), fixing the orchestration first.

## Key Signal

If GPU speedup on the isolated kernel is 10x but E2E speedup is 1.05x, the bottleneck is NOT in the GPU step. Do not optimize the GPU kernel further. Profile the rest of the pipeline and apply Amdahl's Law to identify where the actual time is going.
