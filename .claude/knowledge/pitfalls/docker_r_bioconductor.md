# Docker 构建 R / Bioconductor 踩坑

## 版本匹配（最重要）

- R 版本必须与工具依赖链的 Bioconductor 版本匹配（"R version must match Bioconductor release for dependency chain"）
- R 4.1.2 对应 Bioconductor 3.14，R 4.4+ 对应 3.19+
- TFMPvalue 在 Bioconductor 3.14 被移除但 TFBSTools 3.14 仍依赖它 → 死锁
- 解法：升级到 R 4.4+（jammy-cran40 PPA），不要复用旧 R base 镜像

## 每层必须验证（防静默失败）

BiocManager::install() 失败时 R 退出码仍为 0，Docker 缓存坏层（"BiocManager silent failure caches broken Docker layer"）
```r
BiocManager::install('chromVAR', ask=FALSE)
if (!requireNamespace('chromVAR', quietly=TRUE)) stop('FAILED: chromVAR')
```

## fs 包编译

- fs 需要 libuv 和 cmake（"fs package requires libuv1-dev and cmake for compilation"）
- 解法：系统层安装 `apt-get install -y libuv1-dev cmake`
- 不要依赖 `USE_BUNDLED_LIBUV=1`，R 4.6 下仍需 cmake

## 新 Bioconductor 版本新增依赖

- TFBSTools 在 Bioconductor 3.23 新增 DirichletMultinomial 依赖（"New Bioconductor version may add system-level dependencies requiring libgsl-dev"）
- DirichletMultinomial 需要 `apt-get install -y libgsl-dev`
- 升级 Bioconductor 版本时重新检查全依赖链

## remotes::install_github 与 Bioconductor 包

- remotes 默认只查 CRAN，不认 Bioconductor 包（"remotes::install_github() only searches CRAN by default"）
- GitHub 包依赖 Bioconductor 包时，用 `dependencies=FALSE`（前提：手动预装所有依赖）
- 或 `options(repos=BiocManager::repositories())` 再调用 remotes

## macOS 构建 linux/amd64 镜像

- 必须加 `--platform linux/amd64`，否则默认 arm64（"macOS Docker builds require --platform linux/amd64 flag"）
- BSgenome.Hsapiens.UCSC.hg19 约 677MB，单独一层保留缓存

## 同 tag push

- 集群不会重拉相同 tag 的新内容，换新 tag（v0.1 → v0.1.1）（same-tag Docker push is a no-op on cluster）
