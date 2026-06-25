# Performance Metrics for GPU-Accelerated Bioinformatics Tools

## Primary vs Diagnostic Metrics

**Primary (delivery gate):**
- E2E wall-clock speedup: compare full pipeline CPU vs GPU on same dataset
- If E2E speedup < 1.15x: stop GPU-ification, it is not worth the engineering cost

**Diagnostic (not sufficient for delivery claim):**
- Module/kernel speedup: useful for understanding where time is spent
- Kernel time alone cannot claim success — surrounding overhead must be measured

---

## Measurement Fields

Every benchmark report must record:
- Baseline command and runtime (wall-clock)
- GPU command and runtime (wall-clock)
- E2E speedup ratio
- Module speedup (if measured separately)
- Data transfer time (if measurable)
- Peak GPU memory
- Dataset name and scale
- Hardware (GPU model, RAM)
- Cold run vs warm run distinction

---

## Scaling Behavior

Report speedup at multiple scales when possible:
- Small (smoke test scale)
- Medium (typical real workload)
- Large (stress / VRAM limit)

GPU speedup typically increases with data scale (larger matrices → higher GPU utilization).

---

## Amdahl's Law Ceiling Check (Mandatory)

Before claiming a GPU speedup value, compute the ceiling:

```
Max E2E speedup = 1 / (1 - F + F/S)
```

where:
- F = fraction of total runtime in the GPU-accelerated step
- S = expected kernel speedup

If the ceiling is under 1.15x, do not invest further in GPU-ifying that step.
