"""Histogram / tonal-range image adjustments.

This module implements Lightroom-like tonal controls using the LAB L channel.
Each slider affects a smooth luminance region: Blacks, Shadows, Midtones,
Highlights, and Whites. The overlapping weights avoid hard band boundaries.
"""

from __future__ import annotations

import cv2
import numpy as np


def _gaussian_weight(x: np.ndarray, center: float, sigma: float) -> np.ndarray:
    return np.exp(-0.5 * ((x - center) / sigma) ** 2)


def apply_histogram(
    image_bgr: np.ndarray,
    blacks: float = 0.0,
    shadows: float = 0.0,
    midtones: float = 0.0,
    highlights: float = 0.0,
    whites: float = 0.0,
) -> np.ndarray:
    """Adjust tonal ranges while preserving color as much as possible.

    Slider values are expected in the range [-100, 100]. Positive values
    brighten the target tonal region; negative values darken it.
    """
    if image_bgr is None or image_bgr.size == 0:
        raise ValueError("image_bgr is empty")

    lab = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    lightness = lab[..., 0] / 255.0

    # Smooth overlapping tonal masks. Wider masks in the middle produce a
    # natural transition; narrower masks at the extremes protect contrast.
    weights = np.stack(
        [
            _gaussian_weight(lightness, 0.03, 0.15),
            _gaussian_weight(lightness, 0.25, 0.18),
            _gaussian_weight(lightness, 0.50, 0.20),
            _gaussian_weight(lightness, 0.75, 0.18),
            _gaussian_weight(lightness, 0.97, 0.15),
        ],
        axis=-1,
    )

    # Normalize overlap so a pixel is not accidentally over-adjusted merely
    # because several tonal masks overlap at that luminance.
    weights /= np.maximum(weights.sum(axis=-1, keepdims=True), 1e-6)

    controls = np.array(
        [blacks, shadows, midtones, highlights, whites], dtype=np.float32
    ) / 100.0

    # Max effective shift is ~35% of the L range at slider +/-100.
    # A luminance-dependent headroom factor makes brightening/darkening roll off
    # near pure white/black and reduces clipping.
    signed_strength = np.tensordot(weights, controls, axes=([-1], [0]))
    headroom = np.where(signed_strength >= 0.0, 1.0 - lightness, lightness)
    lightness = lightness + signed_strength * headroom * 0.72
    lightness = np.clip(lightness, 0.0, 1.0)

    lab[..., 0] = lightness * 255.0
    return cv2.cvtColor(lab.astype(np.uint8), cv2.COLOR_LAB2BGR)
