# R kernel environment

The DeepAgent coding agent executes Python and shell commands locally with its `execute` tool. A step assigned the `r-execution` skill also gets an `r` tool backed by a persistent Jupyter R kernel. TissueAgent starts that kernel gateway only when an R step runs.

By default the R gateway runs locally. In the web Settings page, **Docker for R steps** runs the R gateway in the image defined by [`docker/Dockerfile`](docker/Dockerfile). The equivalent CLI switches are `--docker` and `--no-docker`. They do not change where DeepAgent shell commands run.

The Docker image includes IRkernel and R packages used by the spatial analysis skills. It bind-mounts `workspace/` at `/workspace`. The first use may build the image; subsequent runs reuse it. The container is stopped when the server or CLI exits. A local gateway uses the host R installation and needs IRkernel installed.

To add an R package to the Docker environment, use `docker exec tissueagent-sandbox Rscript -e 'install.packages("<package>", repos="https://cloud.r-project.org")'` while the R gateway is running.
