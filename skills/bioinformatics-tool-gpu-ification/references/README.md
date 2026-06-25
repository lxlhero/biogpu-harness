# References

This directory contains reusable, cross-project methodology for GPU acceleration of bioinformatics tools.

## Active Files

| File | Description |
|------|-------------|
| `gpu_porting_principles.md` | Core GPU porting philosophy and decision criteria |
| `bottleneck_analysis.md` | Bottleneck identification framework and Amdahl's Law |
| `gpu_suitability.md` | Decision guide: suitable vs unsuitable operations for GPU |
| `benchmark_design.md` | Benchmark tiers, real-data requirements, user benchmark protocol |
| `validation_metrics.md` | Accuracy thresholds per output type; float path matching strategy |
| `performance_metrics.md` | E2E vs kernel speedup measurement methodology |
| `common_failure_modes.md` | 15 common GPU-ification failure modes with diagnosis and mitigation |
| `bioinformatics_gpu_patterns.md` | Reusable GPU code patterns (vectorize, sparse batch, BLAS, hybrid) |
| `elbo-diagnostic-softmax.md` | ELBO diagnostic recipe for softmax concentration vs numerical bugs |
| `gpu-bug-fix-catalog.md` | Catalog of GPU code bug types found during development |
| `gpu-precision-matching.md` | Float path byte-exact matching (scipy.gmean / torch divergence) |
| `sigma2-trace-correction.md` | Full trace vs diagonal trace for variational Bayes sigma² |
| `standardize-mismatch-bug.md` | Standardize parameter mismatch between CPU and GPU paths |
| `gpu-chunked-processing.md` | Chunked processing for GPU OOM handling |
| `h200-cluster-workflow.md` | H200 cluster rjob workflow, GPFS management, checkpoint pattern |
| `benchmark-data-sources.md` | Public benchmark datasets (1000G, GTEx, UK Biobank) |
| `real-data-benchmark-workflow.md` | End-to-end benchmark workflow with real data |
| `gsmap-case-study.md` | gsMap GPU-ification case study (Python, 15.6x module speedup) |
| `scavenge-case-study.md` | SCAVENGE case study (R, 9.3-100x, reticulate bridge) |
| `gsmap-step3-chromosome-parallelism.md` | Chromosome-level parallelism methodology (reusable) |
| `delegate-task-timeout-strategy.md` | Timeout strategy for delegated tasks |
| `hotspot-guide.txt` | Quick hotspot identification guide |

## Archive

Project-specific operational records (gsMap/susieR E2E scripts, version histories, rjob commands) are in `../archive/`.
