"""
weight_calculator.py
--------------------
Pure functions for computing chargeable weight.
No Django ORM calls — fully unit-testable without DB.
"""

from django.conf import settings


def calculate_volumetric_weight(length: float, width: float, height: float) -> float:
    """
    Volumetric Weight = (L × W × H) / divisor
    Divisor is 5000 by default (industry standard for cm/kg).
    Configurable via settings.VOLUMETRIC_DIVISOR.
    """
    divisor = getattr(settings, "VOLUMETRIC_DIVISOR", 5000)
    return (length * width * height) / divisor


def calculate_chargeable_weight(
    dead_weight: float,
    length: float = 0.0,
    width: float = 0.0,
    height: float = 0.0,
) -> float:
    """
    Returns the chargeable weight: max(dead_weight, volumetric_weight).
    Always enforces a minimum of settings.MINIMUM_CHARGEABLE_WEIGHT (0.5 kg).

    Args:
        dead_weight: Actual weight in kg (required).
        length, width, height: Package dimensions in cm (optional).
            If any are missing/zero, volumetric weight is skipped.

    Returns:
        Chargeable weight in kg (float).

    Raises:
        ValueError: If dead_weight is zero or negative.
    """
    minimum = getattr(settings, "MINIMUM_CHARGEABLE_WEIGHT", 0.5)

    if dead_weight <= 0:
        raise ValueError(f"weight must be positive, got {dead_weight}")

    chargeable = dead_weight

    if length > 0 and width > 0 and height > 0:
        volumetric = calculate_volumetric_weight(length, width, height)
        chargeable = max(dead_weight, volumetric)

    return max(chargeable, minimum)
