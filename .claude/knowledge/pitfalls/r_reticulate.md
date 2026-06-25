# R + reticulate 踩坑

## reticulate 数据传递

- R matrix/vector → Python：用 `np.ascontiguousarray(x, np.float64)` 确保连续内存
- R 传来的 y 向量可能是 (n,1) 2D → Python 侧加 `y = y.squeeze()`
- R logical vector → Python bool array：`np.array(x, dtype=bool)`
- Python numpy array → R：reticulate 自动转，但类型需用 `as.numeric()` 显式转换

## R 调用 Python（py_run_string 路径规则）

- `py_run_string` 里路径必须硬编码，不能用 paste0 拼变量
  因为多层引号嵌套下变量解析失败（paste0 variable expansion breaks inside py_run_string multi-layer quotes）
- 正确：`py_run_string("import sys; sys.path.insert(0, \"/absolute/path\")")`

## bash 内联 R 代码引号规则

三层嵌套（SSH → rjob bash -c → R heredoc）：
  外层：`ssh host bash << 'REMOTE_EOF'`（单引号防本地变量展开）
  R heredoc：`Rscript - <<'"'"'REOF'"'"'`（防 bash -c 内单引号冲突）
  R 代码内路径硬编码，不用 `$VAR`

## R 包输出结构

- 不同版本 R 包返回字段名可能不同，接手前先 `names(result)` 确认
- `get_sigcell_simple` 返回 data.frame，字段：seed_idx、true_cell_top_idx（无 zscore_pvalue）
- susieR `susie()` 返回 `$lbf` 是 length-p vector，GPU wrapper 返回 L×p matrix
  比较时需要 `apply(fg$alpha, 2L, max)` 取 per-variable max

## SUSIER_DEVICE / SCAVENGE_DEVICE 环境变量

- reticulate 在 R 4.4+ 新版本默认用 uv 新建虚拟环境，不用系统 Python
- 修复：在 `/etc/R/Renviron.site` 加 `RETICULATE_PYTHON=/usr/bin/python3`
  或 Dockerfile 里 `echo 'RETICULATE_PYTHON=...' >> /etc/R/Renviron.site`（reticulate R 4.4+ defaults to uv venv — must pin RETICULATE_PYTHON explicitly）
