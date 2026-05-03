import math

from django.conf import settings


def calculate_volumetric_weight(length: float, width: float, height: float) -> float:
    divisor = getattr(settings, "VOLUMETRIC_DIVISOR", 5000)
    return (length * width * height) / divisor


def calculate_chargeable_weight(
    dead_weight: float,
    length: float = 0.0,
    width: float = 0.0,
    height: float = 0.0,
) -> float:
    minimum = getattr(settings, "MINIMUM_CHARGEABLE_WEIGHT", 0.5)
    slab = getattr(settings, "WEIGHT_SLAB_KG", 0.5)

    if dead_weight <= 0:
        raise ValueError(f"weight must be positive, got {dead_weight}")

    chargeable = dead_weight

    if length > 0 and width > 0 and height > 0:
        volumetric_weight = calculate_volumetric_weight(length, width, height)
        chargeable = max(dead_weight, volumetric_weight)

    chargeable = max(chargeable, minimum)

    if slab <= 0:
        raise ValueError(f"WEIGHT_SLAB_KG must be positive, got {slab}")

    return math.ceil(chargeable / slab) * slab
