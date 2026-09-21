"""HSV image adjustment utilities.

OpenCV stores Hue in [0, 179], which represents [0, 360) degrees.
The public API below accepts a hue shift in degrees [-180, 180] and
saturation/value adjustments in percent [-100, 100].
"""

from __future__ import annotations

import cv2
import numpy as np


def apply_hsv(
    image_bgr: np.ndarray,
    hue: float = 0.0,
    saturation: float = 0.0,
    value: float = 0.0,
) -> np.ndarray:
    """Adjust an OpenCV BGR image in HSV color space.

    Args:
        image_bgr: uint8 BGR image.
        hue: Hue rotation in degrees, normally -180..180.
        saturation: Relative saturation change in percent, -100..100.
        value: Relative brightness/value change in percent, -100..100.

    Returns:
        Adjusted uint8 BGR image.
    """
    if image_bgr is None or image_bgr.size == 0:
        raise ValueError("image_bgr is empty")

    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV).astype(np.float32)

    # OpenCV uses H = 0..179 for 0..358 degrees, so divide degrees by 2.
    hue_shift_cv = float(hue) / 2.0
    hsv[..., 0] = np.mod(hsv[..., 0] + hue_shift_cv, 180.0)

    sat_scale = max(0.0, 1.0 + float(saturation) / 100.0)
    val_scale = max(0.0, 1.0 + float(value) / 100.0)

    hsv[..., 1] = np.clip(hsv[..., 1] * sat_scale, 0.0, 255.0)
    hsv[..., 2] = np.clip(hsv[..., 2] * val_scale, 0.0, 255.0)

    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)