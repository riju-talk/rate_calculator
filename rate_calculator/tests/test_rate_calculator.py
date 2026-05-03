"""
Tests for the core rate calculation functions.
Uses unittest.mock to avoid DB dependency for pure charge math.
"""

import math
from unittest.mock import MagicMock
from django.test import TestCase, override_settings
from rate_calculator.services.rate_calculator import (
    calculate_rate_for_courier,
    _calculate_cod_charge,
    _calculate_forward_charge,
    validate_pincode,
)


def make_rate_card(
    base_weight=0.5,
    base_charge=40.0,
    additional_weight_slab=0.5,
    additional_charge=15.0,
    cod_fixed_charge=20.0,
    cod_percent=0.0,
    rto_base_weight=0.5,
    rto_base_charge=0.0,
    rto_additional_weight_slab=0.5,
    rto_additional_charge=0.0,
):
    """Helper to build a mock RateCard without hitting the DB."""
    rc = MagicMock()
    rc.base_weight = base_weight
    rc.base_charge = base_charge
    rc.additional_weight_slab = additional_weight_slab
    rc.additional_charge = additional_charge
    rc.cod_fixed_charge = cod_fixed_charge
    rc.cod_percent = cod_percent
    rc.rto_base_weight = rto_base_weight
    rc.rto_base_charge = rto_base_charge
    rc.rto_additional_weight_slab = rto_additional_weight_slab
    rc.rto_additional_charge = rto_additional_charge
    return rc


class ValidatePincodeTest(TestCase):

    def test_valid_pincode(self):
        validate_pincode("110001")  # should not raise

    def test_short_pincode_raises(self):
        with self.assertRaises(ValueError):
            validate_pincode("1100")

    def test_alpha_pincode_raises(self):
        with self.assertRaises(ValueError):
            validate_pincode("ABCDEF")

    def test_empty_pincode_raises(self):
        with self.assertRaises(ValueError):
            validate_pincode("")


class CodChargeTest(TestCase):

    def test_fixed_wins_over_percent(self):
        rc = make_rate_card(cod_fixed_charge=50.0, cod_percent=1.0)
        # 1% of 1000 = 10 < fixed 50 → cod = 50
        charge = _calculate_cod_charge(rc, 1000)
        self.assertAlmostEqual(charge, 50.0)

    def test_percent_wins_over_fixed(self):
        rc = make_rate_card(cod_fixed_charge=20.0, cod_percent=2.0)
        # 2% of 1500 = 30 > fixed 20 → cod = 30
        charge = _calculate_cod_charge(rc, 1500)
        self.assertAlmostEqual(charge, 30.0)

    def test_zero_order_value_returns_fixed(self):
        rc = make_rate_card(cod_fixed_charge=25.0, cod_percent=1.5)
        charge = _calculate_cod_charge(rc, 0)
        self.assertAlmostEqual(charge, 25.0)

    def test_both_zero(self):
        rc = make_rate_card(cod_fixed_charge=0, cod_percent=0)
        charge = _calculate_cod_charge(rc, 1000)
        self.assertAlmostEqual(charge, 0.0)


class ForwardChargeTest(TestCase):
    """
    Spec example:
        Weight = 1.2 kg
        Base weight = 0.5 kg
        Slabs = ceil((1.2 - 0.5) / 0.5) = ceil(1.4) = 2
        base_charge = 40, additional_charge = 15
        additional = 2 × 15 = 30
    """

    def test_spec_example(self):
        rc = make_rate_card(
            base_weight=0.5, base_charge=40,
            additional_weight_slab=0.5, additional_charge=15,
        )
        result = _calculate_forward_charge(rc, 1.2)
        self.assertEqual(result["base"], 40.0)
        self.assertEqual(result["additional"], 30.0)

    def test_exact_base_weight_no_additional(self):
        rc = make_rate_card(base_weight=0.5, base_charge=40, additional_charge=15)
        result = _calculate_forward_charge(rc, 0.5)
        self.assertEqual(result["additional"], 0.0)

    def test_heavy_parcel(self):
        rc = make_rate_card(
            base_weight=0.5, base_charge=40,
            additional_weight_slab=0.5, additional_charge=10,
        )
        # 5.0 kg → extra = 4.5 kg → 9 slabs × 10 = 90
        result = _calculate_forward_charge(rc, 5.0)
        self.assertEqual(result["additional"], 90.0)


class FullRateTest(TestCase):

    @override_settings(GST_ON_SHIPMENT=0.18)
    def test_prepaid_rate_matches_spec(self):
        rc = make_rate_card(base_charge=40, additional_charge=15, cod_fixed_charge=20)
        rate = calculate_rate_for_courier(rc, 1.2, "prepaid", 0)
        # base=40, additional=30, cod=0, rto=0, subtotal=70, gst=12.6, total=82.6
        self.assertEqual(rate["base"], 40.0)
        self.assertEqual(rate["additional"], 30.0)
        self.assertEqual(rate["cod"], 0.0)
        self.assertAlmostEqual(rate["gst"], 12.6)
        self.assertAlmostEqual(rate["total"], 82.6)

    @override_settings(GST_ON_SHIPMENT=0.18)
    def test_cod_rate(self):
        rc = make_rate_card(
            base_charge=40, additional_charge=15,
            cod_fixed_charge=20, cod_percent=1.5,
        )
        # order_value=1500 → 1.5% = 22.5 > fixed 20 → cod = 22.5
        rate = calculate_rate_for_courier(rc, 1.2, "cod", 1500)
        self.assertAlmostEqual(rate["cod"], 22.5)
        # subtotal = 40 + 30 + 22.5 = 92.5 → gst = 16.65 → total = 109.15
        self.assertAlmostEqual(rate["gst"], 16.65)
        self.assertAlmostEqual(rate["total"], 109.15)
