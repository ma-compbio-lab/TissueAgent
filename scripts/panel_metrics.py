"""Image-similarity metrics for a reproduced figure panel, following the BioFigBench report protocol.

The protocol (BioFigBench-website/reports/figure_reproduce_20260904/README.md):

* Apply EXIF orientation, composite transparency on white, convert to grayscale (done last, after resizing).
* Scale the reference to a maximum long edge of 768 px. Fit the output into that canvas, preserving its
  aspect ratio, centred on white padding. No cropping or registration.
* SSIM: scikit-image defaults, grayscale, data range 255.
* pHash: 32x32 grayscale, orthonormal 2-D DCT, 8x8 low-frequency block thresholded at its median;
  64-bit Hamming distance, similarity = 1 - distance / 64.
* ORB: at most 2000 keypoints per image, cross-checked Hamming matches with distance <= 64, divided by the
  smaller keypoint count; missing descriptors give N/A.

The protocol leaves a few details open (interpolation, the order of resizing and grayscale conversion, whether
a small reference is enlarged). The choices below were fixed by checking them against the scores the report
already published; ``scripts/validate_panel_metrics.py`` re-runs that check. SSIM and pHash reproduce
exactly. ORB reproduces the keypoint counts exactly and the match counts to within a few matches (median
difference one), so ORB scores computed here can differ from the published pipeline's in the third decimal.
"""

from __future__ import annotations

import cv2
import numpy as np
from PIL import Image, ImageOps
from scipy.fft import dctn
from skimage.metrics import structural_similarity

MAX_EDGE = 768
PHASH_SIZE = 32
PHASH_BLOCK = 8
ORB_FEATURES = 2000
ORB_MAX_DISTANCE = 64


def load_rgb(path) -> Image.Image:
    """EXIF-orient the image and flatten any transparency onto white."""
    image = ImageOps.exif_transpose(Image.open(path)).convert("RGBA")
    canvas = Image.new("RGBA", image.size, (255, 255, 255, 255))
    canvas.alpha_composite(image)
    return canvas.convert("RGB")


def common_canvas(reference: Image.Image, generated: Image.Image) -> tuple[np.ndarray, np.ndarray]:
    """Scale the reference to MAX_EDGE, letterbox the generated image onto the same canvas, go grayscale.

    Resizing is done on the colour image with Lanczos resampling and the grayscale conversion comes
    last; this ordering is the one that reproduces the published SSIM and pHash values exactly.
    """
    if max(reference.size) > MAX_EDGE:
        reference = ImageOps.contain(reference, (MAX_EDGE, MAX_EDGE), method=Image.Resampling.LANCZOS)
    padded = ImageOps.pad(
        generated, reference.size, method=Image.Resampling.LANCZOS, color=(255, 255, 255), centering=(0.5, 0.5)
    )
    return np.asarray(reference.convert("L")), np.asarray(padded.convert("L"))


def phash_bits(gray: np.ndarray) -> np.ndarray:
    small = np.asarray(Image.fromarray(gray).resize((PHASH_SIZE, PHASH_SIZE), Image.LANCZOS), dtype=np.float64)
    block = dctn(small, norm="ortho")[:PHASH_BLOCK, :PHASH_BLOCK]
    return (block > np.median(block)).flatten()


def orb_similarity(ref: np.ndarray, gen: np.ndarray) -> dict:
    orb = cv2.ORB_create(nfeatures=ORB_FEATURES)
    kp_ref, des_ref = orb.detectAndCompute(ref, None)
    kp_gen, des_gen = orb.detectAndCompute(gen, None)
    out = {"reference_keypoints": len(kp_ref), "generated_keypoints": len(kp_gen), "orb_matches": None, "orb_similarity": None}
    if des_ref is None or des_gen is None or not len(kp_ref) or not len(kp_gen):
        return out
    matches = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(des_ref, des_gen)
    good = sum(1 for m in matches if m.distance <= ORB_MAX_DISTANCE)
    out["orb_matches"] = good
    out["orb_similarity"] = good / min(len(kp_ref), len(kp_gen))
    return out


def score(reference_path, generated_path) -> dict:
    """SSIM, pHash and ORB similarity of a generated panel against its published reference."""
    ref, gen = common_canvas(load_rgb(reference_path), load_rgb(generated_path))
    distance = int(np.count_nonzero(phash_bits(ref) != phash_bits(gen)))
    result = {
        "ssim": float(structural_similarity(ref, gen, data_range=255)),
        "phash_distance": distance,
        "phash_similarity": 1 - distance / (PHASH_BLOCK * PHASH_BLOCK),
    }
    result.update(orb_similarity(ref, gen))
    return result
