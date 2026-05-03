"""
Tests for weight_calculator.py
Pure unit tests — no database, no Django ORM.
"""

from django.test import TestCase, override_settings
from rate_calculator.services.weight_calculator import (
    calculate_chargeable_weight,
    calculate_volumetric_weight,
)


class VolumetricWeightTest(TestCase):

    def test_standard_volumetric(self):
        # 20 × 15 × 10 = 3000 cm³ / 5000 = 0.6 kg
        result = calculate_volumetric_weight(20, 15, 10)
        self.assertAlmostEqual(result, 0.6)

    def test_large_package(self):
        # 50 × 50 × 50 = 125000 / 5000 = 25.0 kg
        result = calculate_volumetric_weight(50, 50, 50)
        self.assertAlmostEqual(result, 25.0)

    @override_settings(VOLUMETRIC_DIVISOR=6000)
    def test_custom_divisor(self):
        # 60 × 50 × 40 = 120000 / 6000 = 20.0 kg
        result = calculate_volumetric_weight(60, 50, 40)
        self.assertAlmostEqual(result, 20.0)


class ChargeableWeightTest(TestCase):

    def test_dead_weight_wins(self):
        # dead=5kg, volumetric=0.6kg → chargeable = 5.0
        result = calculate_chargeable_weight(5.0, 20, 15, 10)
        self.assertAlmostEqual(result, 5.0)

    def test_volumetric_wins(self):
        # dead=1kg, volumetric=25kg → chargeable = 25.0
        result = calculate_chargeable_weight(1.0, 50, 50, 50)
        self.assertAlmostEqual(result, 25.0)

    def test_minimum_weight_enforced(self):
        # 0.1 kg < 0.5 kg minimum → should return 0.5
        result = calculate_chargeable_weight(0.1)
        self.assertAlmostEqual(result, 0.5)

    def test_no_dimensions_uses_dead_weight(self):
        result = calculate_chargeable_weight(1.2)
        self.assertAlmostEqual(result, 1.2)

    def test_zero_dimension_skips_volumetric(self):
        # Only 2 of 3 dimensions → skip volumetric
        result = calculate_chargeable_weight(2.0, 30, 20, 0)
        self.assertAlmostEqual(result, 2.0)

    def test_negative_weight_raises(self):
        with self.assertRaises(ValueError):
            calculate_chargeable_weight(-1.0)

    def test_zero_weight_raises(self):
        with self.assertRaises(ValueError):
            calculate_chargeable_weight(0)

    @override_settings(MINIMUM_CHARGEABLE_WEIGHT=1.0)
    def test_custom_minimum(self):
        result = calculate_chargeable_weight(0.5)
        self.assertAlmostEqual(result, 1.0)
