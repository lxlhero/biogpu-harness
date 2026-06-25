# GPU 加速核心方法论

> 本文件是运行时短摘要。详版见：
> - `skills/bioinformatics-tool-gpu-skills/references/bottleneck_analysis.md`
> - `skills/bioinformatics-tool-gpu-skills/references/bioinformatics_gpu_patterns.md`

## 1. 分析框架：Amdahl's Law

GPU 化前必须先算 E2E 预期收益，不到 15% 不做：

  E2E_speedup = 1 / ((1 - P) + P / S)
  P = 可 GPU 化模块占 E2E 总时间比例
  S = 该模块预估 GPU 加速倍数

例：模块占 65%，GPU 加速 50× → E2E = 1/(0.35 + 0.65/50) = 2.75×
例：模块占 3%，GPU 加速 200× → E2E = 1/(0.97 + 0.03/200) = 1.03×（不值得）


## 2. Profiling 方法

- R 工具：Rprof / profvis
- Python 工具：cProfile / py-spy
- 必须在集群真实数据上跑，不用合成数据
- 过滤 < 10% E2E 占比的模块，不做无效工作


## 3. GPU 代码模式

**Pattern 1：串行循环 → batch CUDA（最高价值）**
  N 次独立同类计算合并为 1 次 batch 操作
  例：1000 次置换随机游走 → 1 次 batch sparse.mm（SCAVENGE，~100×）

**Pattern 2：稀疏图传播 batch 化**
  torch.sparse_csr_tensor + batched sparse.mm
  P0 = [p0_1 | p0_2 | ... | p0_N]（列堆叠），一次完成 N 次传播

**Pattern 3：BLAS 替换（R 矩阵运算）**
  tcrossprod / crossprod → torch.mm / torch.mv
  关键：必须与原版 BLAS 路径数值一致，不只是数学等价

**Pattern 4：Hybrid CPU+GPU（默认策略）**
  不要 GPU 化所有步骤，只做热点
  scipy rankdata CPU 比 GPU 快 20×，保留在 CPU


## 4. 调试流程

1. 本地合成小数据测试（"不崩溃"），CPU device 运行排除 CUDA 问题
2. 打印中间值，逐步对齐与原版的数值路径
3. 通过后再上集群，不要在集群上 debug
4. 精度通过后再测速度，不能颠倒


## 5. 镜像分层策略

  L0  nvidia/cuda 上游基础镜像
  L1  语言运行时 + 科学计算栈（R/Python + PyTorch）
  L2  项目 GPU kernel（~50KB 增量层）

调试期：L1 base + GPFS mount kernel（不重建镜像，改代码秒级生效）
发布前：kernel 内化进 L2，一次 build 永久固化
