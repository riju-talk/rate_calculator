"""
test_services.py
----------------
Additional service-layer tests covering zone resolution and integration
between weight calculator, zone resolver, and rate calculator.
"""

from django.test import TestCase
from unittest.mock import patch, MagicMock
from shipping.services.weight_calculator import calculate_chargeable_weight
from shipping.services.zone_resolver import resolve_zone
from shipping.services.rate_calculator import calculate_rate_for_courier


class WeightCalculatorTest(TestCase):

    def test_dead_weight_wins(self):
        self.assertEqual(calculate_chargeable_weight(2.0, 10, 10, 10), 2.0)

    def test_volumetric_wins(self):
        # 50 × 50 × 50 / 5000 = 25 kg > 1 kg dead weight
        self.assertEqual(calculate_chargeable_weight(1.0, 50, 50, 50), 25.0)

    def test_minimum_weight(self):
        self.assertEqual(calculate_chargeable_weight(0.1), 0.5)

    def test_no_dimensions(self):
        self.assertEqual(calculate_chargeable_weight(1.2), 1.2)


class ZoneResolverTest(TestCase):

    def test_local_zone(self):
        # Same 3-digit prefix → local
        self.assertEqual(resolve_zone("110001", "110002"), "local")

    def test_special_zone_ne(self):
        # 790XXX = Arunachal Pradesh → special
        self.assertEqual(resolve_zone("110001", "790001"), "special")

    def test_special_zone_jk(self):
        # 190XXX = J&K → special
        self.assertEqual(resolve_zone("110001", "190001"), "special")

    def test_metro_zone(self):
        # Delhi (110) → Mumbai (400) = metro
        self.assertEqual(resolve_zone("110001", "400001"), "metro")

    def test_state_zone(self):
        # Same 2-digit prefix but different 3-digit → state
        self.assertEqual(resolve_zone("110001", "120001"), "state")

    def test_roi_zone(self):
        # Delhi → non-metro non-NE → roi
        self.assertEqual(resolve_zone("110001", "302001"), "roi")


class RateCalculationTest(TestCase):

    def _make_rate_card(self, **kwargs):
        rc = MagicMock()
        rc.base_weight = kwargs.get("base_weight", 0.5)
        rc.base_charge = kwargs.get("base_charge", 40)
        rc.additional_weight_slab = kwargs.get("slab", 0.5)
        rc.additional_charge = kwargs.get("additional_charge", 15)
        rc.cod_fixed_charge = kwargs.get("cod_fixed", 20)
        rc.cod_percent = kwargs.get("cod_percent", 0)
        return rc

    def test_prepaid_rate(self):
        rc = self._make_rate_card()
        rate = calculate_rate_for_courier(rc, 1.2, "prepaid", 0)
        # extra = 1.2 - 0.5 = 0.7 → 2 slabs × 15 = 30. base=40 total_before_gst=70
        self.assertEqual(rate["base"], 40)
        self.assertEqual(rate["additional"], 30)
        self.assertEqual(rate["cod"], 0)

    def test_cod_rate(self):
        rc = self._make_rate_card(cod_fixed=20, cod_percent=1.5)
        rate = calculate_rate_for_courier(rc, 1.0, "cod", 1500)
        # 1.5% of 1500 = 22.5 > fixed 20 → cod = 22.5
        self.assertEqual(rate["cod"], 22.5)