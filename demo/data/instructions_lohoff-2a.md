# Lohoff Fig. 2a inputs

The two CSV files contain the authors' genuine joint UMAP coordinates and cell-type labels. The atlas has 16,861 cells; seqFISH has 57,536 cells from three embryos. These are processed plotting data, not raw atlas expression. The author figure excludes the 4,968 seqFISH cells labeled Low quality.

The original demo AnnData is also supplied, unchanged (19,416 seqFISH cells, 351 genes). Its stored embedding differs from the published joint embedding. All its cell IDs and cell-type labels match the author table. Use the two CSVs together for this joint figure; do not mix coordinate systems.

Source: https://content.cruk.cam.ac.uk/jmlab/SpatialMouseAtlas2020/MGA_joint_UMAP.Rds
Paper: https://doi.org/10.1038/s41587-021-01006-2
