# Bioinformatics GPU Patterns

Reusable implementation patterns for GPU-accelerating bioinformatics tools. Each pattern addresses a recurring structure found in statistical genomics and spatial transcriptomics workflows.

---

## Cross-language Strategy for R Tools

For R packages, do NOT rewrite the entire tool in Python or CUDA. Instead:

1. Write a Python module containing only the GPU-accelerated core functions.
2. R calls into Python via `reticulate` for hotspot functions only.
3. R retains control flow, file I/O, argument parsing, and post-processing.
4. File convention: `<tool>/<tool>_gpu.py`

This strategy minimizes risk, preserves the original tool's behavior outside the hotspot, and keeps the GPU layer small and testable in isolation.

---

## Pattern 1: Vectorized Per-Sample Loop → Batch CUDA

Replace serial per-element loops with a single batched tensor operation.

```python
# WRONG: per-spot loop — 360ms for 5000 spots
for p in range(N):
    sims[p] = F.cosine_similarity(latent[p:p+1], latent[neighbors[p]])

# RIGHT: vectorized — 0.5ms for 5000 spots
neigh_latent = latent[neigh_idx]          # (N, K, D)
sims = F.cosine_similarity(
    latent.unsqueeze(1), neigh_latent, dim=2  # (N, K)
)
```

The key insight: gather neighbor tensors first, then operate on the full (N, K, D) batch in one call. Avoid any Python loop over N.

---

## Pattern 2: Sparse Graph Propagation Batched Over Traits

When running random-walk or label-propagation over a graph for many independent trait vectors, batch all traits into a single matrix multiply instead of iterating over traits.

```python
Wt = torch.sparse_csr_tensor(...).cuda()      # graph weight matrix, loaded once
P = p0_batch_tensor                            # (n_cells, n_traits), all traits at once

for _ in range(n_iter):
    P = alpha * torch.sparse.mm(Wt, P) + (1 - alpha) * p0_batch_tensor
```

The graph matrix `Wt` is a constant; load it to GPU once and reuse across all traits. This avoids N separate propagation runs.

**Note:** PyTorch 2.3.1 does not have `torch.sparse.mv()`. For single-vector inputs, use `torch.mv()` (dense) or reshape to (n, 1) and use `torch.sparse.mm()`.

---

## Pattern 3: BLAS Replacement

Replace R BLAS calls (`tcrossprod`, `crossprod`) with PyTorch equivalents when the matrix is large enough to justify GPU transfer.

| R call | PyTorch equivalent |
|---|---|
| `tcrossprod(X)` | `torch.mm(X, X.T)` |
| `crossprod(X, b)` | `torch.mv(X.T, b)` or `torch.mm(X.T, b)` |
| `X %*% Y` | `torch.mm(X, Y)` |

Match the EXACT BLAS call sequence of the original implementation. Mathematical equivalence is not sufficient — intermediate shapes and operation order must match to preserve numerical agreement with the reference.

---

## Pattern 4: CPU/GPU Hybrid (Default Strategy)

Profile each step independently. Keep steps that are already fast on CPU. GPU only steps that are compute-dominated and have sufficient input size.

```
CPU:  rank normalization (fast with scipy, small overhead)
GPU:  batch similarity scoring (slow Python loop → single torch.mm)
CPU:  output formatting, file writing
```

Avoid the reflex to move everything to GPU. Each CPU-to-GPU transition costs transfer time. The hybrid approach keeps transfers rare and targeted.

---

## Device Toggle Pattern

Expose a single environment variable to switch between GPU and CPU execution:

```
<TOOL>_DEVICE=gpu   # use GPU path
<TOOL>_DEVICE=cpu   # use CPU path (default fallback)
```

The CPU path must delegate to the ORIGINAL tool implementation, not a Python reimplementation. A reimplementation introduces a new source of bugs and removes the ability to use the original as a correctness reference.

```python
def run_hotspot(data, device=None):
    if device is None:
        device = os.environ.get("MYTOOL_DEVICE", "cpu")
    if device == "gpu" and torch.cuda.is_available():
        return _run_hotspot_gpu(data)
    else:
        return original_tool.run_hotspot(data)  # delegate, do not reimplement
```
