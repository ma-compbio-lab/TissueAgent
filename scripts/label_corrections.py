"""Hand corrections to the keyword-based panel labels shown in the Benchmark Statistics section.

BioFigBench's statistics label each panel's spatial technology and auxiliary data by matching keywords
(platform names, "scRNA-seq", "H&E", ...) against the panel's data records and, if those say nothing, its
caption and methods. The paper title is not read, and a dataset that is described by its name or accession
("PDAC-A ST1", "V1_Mouse_Brain_Sagittal_Anterior") rather than by its platform matches nothing, so the
panel falls into "Other / unspecified" or "None identified". The reverse also happens: the
legacy Spatial Transcriptomics rule matches the plain phrase "spatial transcriptomics", so a paper that says
"10X Visium for FFPE spatial transcriptomics" gets tagged with the original ST platform by mistake, and a
panel whose methods mention Visium for other datasets can be tagged Visium although its own data are ST.
A correction therefore either adds a label ("to"), removes a wrong one ("remove"), or both.

A data type counts for a panel when the panel's own caption or methods name it (or its data records do).
Derived results that only exist upstream of the panel do not count. The entries below fix the cases where
that evidence settles the answer. Every entry states the evidence it rests on. Labels use the package's own
vocabulary. Panels not listed keep the package's labels.
"""

from __future__ import annotations

OTHER = "Other / unspecified"
NONE = "No auxiliary modality identified"

MERFISH = "MERFISH/MERSCOPE"
VISIUM = "Visium"
ST = "legacy Spatial Transcriptomics"
SC_REFERENCE = "scRNA-seq reference"
FLUORESCENCE = "immunofluorescence/protein imaging"
MICROSCOPY = "microscopy/source images"
PROTEOMICS = "CODEX/spatial proteomics"
REFERENCE_PROFILES = "cell-type reference profiles"  # not in the package vocabulary; used for SpatialDecon's reference matrices

CORRECTIONS = [
    # ---- spatial technology: the platform is not named in the panel's records ----
    {
        "field": "technologies",
        "to": MERFISH,
        "panels": [
            ("s41586-021-03705-x", "Extended_Data_Fig_4a"),
            ("s41586-021-03705-x", "Extended_Data_Fig_10d"),
            ("s41586-021-03705-x", "Fig_3e"),
        ],
        "reason": (
            "The paper is a MERFISH atlas of the mouse motor cortex. This panel's data records "
            "(counts.h5ad, cell_labels.csv, segmented cell boundaries) name the dataset but not the platform."
        ),
    },
    {
        "field": "technologies",
        "to": ST,
        "panels": [("s41587-022-01273-7", "Fig_3b")],
        "reason": (
            "The data are Ståhl et al. 2016 mouse olfactory bulb replicate 12, i.e. the original "
            "microarray-based Spatial Transcriptomics (ST) platform. The records give the dataset, not the platform."
        ),
    },
    {
        "field": "technologies",
        "to": ST,
        "panels": [("s41587-022-01273-7", "Fig_4f")],
        "reason": (
            "The records are 'PDAC-A ST1' spatial counts (GEO GSM3036911). 'ST' is the microarray-based "
            "Spatial Transcriptomics platform, which the rule does not match when abbreviated."
        ),
    },
    {
        "field": "technologies",
        "to": ST,
        "panels": [("s41467-022-30033-z", "Fig_4a")],
        "reason": "The record is an 'MOB ST count matrix' (mouse olfactory bulb, replicate 8), abbreviated 'ST'.",
    },
    {
        "field": "technologies",
        "to": ST,
        "panels": [("s41467-022-30033-z", "Fig_5c")],
        "reason": "The records are 'Breast-cancer ST count matrix' files (layers 1-4), abbreviated 'ST'.",
    },
    {
        "field": "technologies",
        "to": ST,
        "panels": [("s41592-021-01255-8", "Fig_2a")],
        "reason": "The records are 'PDAC-B ST1' spatial counts, expression table and H&E image (GEO GSM3405534).",
    },
    {
        "field": "technologies",
        "to": VISIUM,
        "panels": [("s41592-021-01255-8", "Fig_5b")],
        "reason": (
            "The records are 10x Genomics 'V1_Mouse_Brain_Sagittal' sample files (filtered_feature_bc_matrix, "
            "spatial bundle, tissue image), the Visium output format; the word 'Visium' does not appear."
        ),
    },
    {
        "field": "technologies",
        "to": ST,
        "remove": VISIUM,
        "panels": [
            ("s41587-021-00935-2", "Fig_3c"),
            ("s41587-021-00935-2", "Fig_3d"),
            ("s41587-021-00935-2", "Fig_3e"),
        ],
        "reason": (
            "The panel's data record is the 'Melanoma ST count/coordinate archive' (sample ST_mel1_rep2), the older "
            "microarray-based ST platform. The methods mention Visium only for the paper's other datasets (Fig. 2c, 4b, 5b)."
        ),
    },
    {
        "field": "technologies",
        "remove": ST,
        "panels": [
            ("s41551-025-01437-1", "Extended_Data_Fig_10c"),
            ("s41551-025-01437-1", "Extended_Data_Fig_3b"),
            ("s41551-025-01437-1", "Extended_Data_Fig_7b"),
            ("s41551-025-01437-1", "Extended_Data_Fig_9"),
            ("s41551-025-01437-1", "Fig_3c"),
            ("s41551-025-01437-1", "Fig_5b"),
            ("s41551-025-01437-1", "Fig_7a"),
        ],
        "reason": (
            "The methods name the platform as '10X Visium for FFPE spatial transcriptomics' (Visium FFPE or CytAssist on "
            "H&E-imaged sections). The rule matched the generic phrase 'spatial transcriptomics' and added the original ST "
            "platform by mistake; Visium is the correct label."
        ),
    },
    {
        "field": "technologies",
        "to": ST,
        "panels": [("s41592-024-02284-9", "Fig_3h")],
        "reason": "The records are the 'P2_ST_rep2' spatial expression matrix and spots (GEO GSM4284317), an ST slide.",
    },
    # ---- auxiliary data: the records name another data type in words the rule does not match ----
    {
        "field": "modalities",
        "to": SC_REFERENCE,
        "panels": [("s41587-022-01273-7", "Fig_4f")],
        "reason": "The records include a matched PDAC-A inDrop reference expression matrix (GEO GSE111672), a single-cell reference.",
    },
    {
        "field": "modalities",
        "to": SC_REFERENCE,
        "panels": [("s41587-023-01697-9", "Extended_Data_Fig_9c")],
        "reason": "The records include a mouse-kidney single-cell expression matrix used as the CytoSPACE reference atlas.",
    },
    {
        "field": "modalities",
        "to": FLUORESCENCE,
        "panels": [("s41587-021-00935-2", "Fig_4b"), ("s41587-021-00935-2", "Fig_5b")],
        "reason": "The records include a matched DAPI/CD3 tissue image, a fluorescence image of the same section.",
    },
    {
        "field": "modalities",
        "to": MICROSCOPY,
        "panels": [("s41551-024-01205-7", "Extended_Data_Fig_1a"), ("s41551-024-01205-7", "Fig_2b")],
        "reason": "The records include conventional in situ hybridization (ISH) images that the panel is compared against.",
    },
    {
        "field": "modalities",
        "to": REFERENCE_PROFILES,
        "panels": [("s41467-022-28020-5", "Fig_5h"), ("s41467-022-28020-5", "Fig_5i")],
        "reason": (
            "The panel's methods say SpatialDecon was applied 'with SafeTME and tumour-specific profiles', "
            "that is, reference cell-type expression profiles, to the GeoMx data."
        ),
    },
    {
        "field": "modalities",
        "to": PROTEOMICS,
        "panels": [("s41551-024-01205-7", "Extended_Data_Fig_10a"), ("s41551-024-01205-7", "Extended_Data_Fig_10g")],
        "reason": (
            "The caption describes co-detection of 30 immune-related proteins with 6 marker mRNAs in DLBCL "
            "sections (antibody tags read out through the MiP-seq workflow); panel g plots CD27, CD45RA, CCR7 and CXCR6."
        ),
    },
    {
        "field": "modalities",
        "to": PROTEOMICS,
        "panels": [
            ("s41551-024-01205-7", "Extended_Data_Fig_10b"),
            ("s41551-024-01205-7", "Extended_Data_Fig_10d"),
            ("s41551-024-01205-7", "Extended_Data_Fig_10e"),
        ],
        "reason": (
            "The clusters come from the single-cell expression profile of the DLBCL protein-RNA co-detection "
            "experiment in panel a (30 antibody tags with 6 mRNAs), and the panel's methods include the co-detection protocol."
        ),
    },
]

# Panels that looked as if they might use another data type, were checked against their own caption and
# methods, and stay "Spatial data only". An audit record: nothing reads it, and the page does not show it.
CHECKED_SPATIAL_ONLY = [
    {
        "panels": [("s41592-022-01575-3", "Fig_5e")],
        "reason": (
            "The panel plots observed CXCL13 counts per Visium spot. Its description says it deliberately shows observed "
            "expression, not the cell-type-specific fit that C-SIDE produces, so it uses the spatial data alone."
        ),
    },
    {
        "panels": [("s41587-021-01006-2", "Fig_2d"), ("s41587-021-01006-2", "Fig_2e")],
        "reason": (
            "The methods describe only seqFISH cell segmentation, neighbourhood networks and expression quantification. "
            "The cell types they use are 'mapped' annotations, an upstream result rather than a dataset these panels read."
        ),
    },
    {
        "panels": [("s41467-022-28020-5", "Fig_6d"), ("s41467-022-28020-5", "Fig_6h")],
        "reason": (
            "The records list only the GeoMx count matrix and AOI coordinates. The cell-abundance estimates the methods regress "
            "on come from the Fig. 5 deconvolution, a derived result rather than a separate data type."
        ),
    },
]

_PLACEHOLDER = {"technologies": OTHER, "modalities": NONE}


def corrections_for(article: str, panel: str) -> list[dict]:
    return [c for c in CORRECTIONS if (article, panel) in c["panels"]]


def apply(article: str, panel: str, technologies: list[str], modalities: list[str]) -> tuple[list[str], list[str], list[dict]]:
    """Return the corrected labels and one record per change actually made."""
    labels = {"technologies": list(technologies), "modalities": list(modalities)}
    changes = []
    for correction in corrections_for(article, panel):
        field, new, remove = correction["field"], correction.get("to"), correction.get("remove")
        before = list(labels[field])
        after = [x for x in before if x != remove]
        if new and new not in after:
            after = [x for x in after if x != _PLACEHOLDER[field]] + [new]
        after = after or [_PLACEHOLDER[field]]
        if after == before:
            continue
        labels[field] = after
        changes.append(
            {
                "article": article,
                "panel": panel,
                "field": "technology" if field == "technologies" else "auxiliary",
                "from": before,
                "to": after,
                "reason": correction["reason"],
            }
        )
    return labels["technologies"], labels["modalities"], changes
