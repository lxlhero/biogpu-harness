# GPU Porting Principles

## Core Philosophy

GPU-ification requires profiling first, not assumption. Never start GPU work without identifying the actual bottleneck through measurement.

Prioritize end-to-end (E2E) speedup over isolated kernel speedup. A 100x faster kernel that covers 4% of runtime yields only a 1.04x E2E gain. Use Amdahl's Law to estimate ceiling before any implementation work.

Correctness before speed. Validate precision against the ORIGINAL tool's output, not a parallel reimplementation. Both a reimplementation and a GPU version can silently agree on a wrong answer. The ground truth is always the original CPU tool.

## When NOT to GPU-ify

Do not GPU-ify I/O-bound steps. If more than 80% of runtime is file I/O (reading PLINK, BGEN, CSV, etc.), GPU acceleration saves nothing — the bottleneck is the disk, not compute.

CPU/GPU data transfer cost must always be factored in. Moving data across the PCIe bus has real latency. If the step is short, transfer overhead can exceed computation time.

Do not use synthetic or toy data for correctness validation. Synthetic data is acceptable only for smoke tests ("does the code crash?"). Real precision claims require realistic inputs that match the true distribution of the tool's production inputs.

## When to GPU-ify

GPU-ify only when ALL of the following hold:

1. The target hotspot accounts for more than 30% of total runtime.
2. The operation has high parallelism (independent elements, matrix ops, batch scoring).
3. Data can be reshaped into contiguous GPU-friendly tensors.
4. Data transfer cost is small relative to the compute saved.
5. Numerical precision can be maintained within acceptable tolerance of the original.

If any condition fails, fix that condition first or accept that GPU-ification is not warranted for this step.
