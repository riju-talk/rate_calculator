from django.test import TestCase, override_settings

from rate_calculator.services.weight_calculator import (
    calculate_chargeable_weight,
    calculate_volumetric_weight,
)


class WeightCalculatorTest(TestCase):
    def test_volumetric_weight(self):
        self.assertAlmostEqual(calculate_volumetric_weight(20, 15, 10), 0.6)

    @override_settings(VOLUMETRIC_DIVISOR=6000)
    def test_volumetric_weight_uses_settings_divisor(self):
        self.assertAlmostEqual(calculate_volumetric_weight(60, 50, 40), 20.0)

    def test_dead_weight_wins(self):
        self.assertAlmostEqual(calculate_chargeable_weight(5.0, 20, 15, 10), 5.0)

    def test_volumetric_weight_wins(self):
        self.assertAlmostEqual(calculate_chargeable_weight(1.0, 50, 50, 50), 25.0)

    def test_minimum_weight_floor(self):
        self.assertAlmostEqual(calculate_chargeable_weight(0.1), 0.5)

    @override_settings(MINIMUM_CHARGEABLE_WEIGHT=1.0)
    def test_minimum_weight_floor_uses_settings(self):
        self.assertAlmostEqual(calculate_chargeable_weight(0.5), 1.0)

    def test_missing_dimension_skips_volumetric_weight(self):
        self.assertAlmostEqual(calculate_chargeable_weight(1.2, 20, 15, 0), 1.2)

    def test_negative_weight_raises(self):
        with self.assertRaises(ValueError):
            calculate_chargeable_weight(-1.0)

    def test_zero_weight_raises(self):
        with self.assertRaises(ValueError):
            calculate_chargeable_weight(0)
