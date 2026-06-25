# GPU Kernel 通用踩坑（gpu-code-reviewer P1/P2 必读）

## P1 — 算法路径对齐（精度核心）

**必须匹配原版数值路径，数学等价 ≠ 数值等价**

- 原版预计算了 Gram 矩阵 XtX 就用 XtX，不要拆成两次 MV（"Match the original numerical path, not just mathematical equivalence"）
- sigma² 更新用全 trace 而不是对角近似（"Diagonal trace approximation breaks on real correlated data"）
  对角近似在 XtX 近似单位矩阵时等价，真实 LD 数据下系统偏高 20-70%
- 标准化参数要与 CPU 路径对齐：standardize=FALSE 要在双方一致（"Standardize parameter mismatch between CPU and GPU paths"）
- float64 全程，不允许隐式降精度

**置换检验（permutation test）精度判断规则**
- 100 perm CPU-vs-CPU Jaccard ≈ 0.59，是正常采样方差，不是 bug
- 精度验证必须用 ≥1000 perm，Jaccard > 0.80 为 PASS（"Permutation-based methods require ≥1000 permutations for precision validation"）
- 度分层采样（degree-stratified）不等于均匀随机采样（"Degree-stratified sampling is not equivalent to uniform random sampling"）


## P2 — 常见 GPU Bug

**torch.diag() vs .diagonal()**
- `torch.diag(large_tensor)` 在 CUDA 大张量上触发 expand 错误
- 修复：改用 `tensor.diagonal()`（"torch.diag() on large CUDA tensors triggers expand error"）

**reticulate 传入向量维度**
- R 通过 reticulate 传 y 向量可能是 (n,1) 2D
- 防御：`y = y.squeeze()` 确保 1D（Bug #3）

**sparse 操作**
- `torch.sparse.mv()` 在 PyTorch 2.3.1 不存在，用 `torch.mv()` 或 `torch.sparse.mm()`（pitfall pattern）
- scipy CSR `multiply()` 返回 COO → 必须 `.tocsr()` 后再使用

**归一化方向**
- 行归一化 vs 列归一化：必须与原版一致
- SCAVENGE randomWalk_sparse 用列归一化 `t(t(W)/colSums(W))`，不是行归一化

**gamma 方向**
- RWR 正确公式：`(1-gamma) * W^T @ P + gamma * P0`（95% 传播 + 5% 重启）
- 写反成 `gamma * W^T + (1-gamma) * P0` 会导致几乎无传播，GPU 输出接近 P0


## P3 — CPU/GPU 切换实现

- 必须通过环境变量 `<TOOL>_DEVICE=gpu|cpu` 控制分支
- CPU 路径委托给原版实现，不自己重写
- rjob 通过 `--env TOOL_DEVICE=gpu` 切换，不改代码


## P4 — 性能（建议性，不阻塞）

- 不用 Python for 循环逐元素操作大矩阵
- batch 优先：1000 次串行 SpMV → 1 次 batch sparse.mm（SCAVENGE 模式）
- 数据在 GPU 上预加载，不在循环内反复 `.to(device)`
- 小数据（< 10K 元素）GPU 通常慢于 CPU（kernel launch overhead）
