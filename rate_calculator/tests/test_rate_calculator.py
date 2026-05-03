from unittest.mock import MagicMock

from django.core.cache import cache
from django.test import TestCase, override_settings

from rate_calculator.models import Courier, CourierServiceability, RateCard
from rate_calculator.services.rate_calculator import (
    calculate_rate_for_courier,
    calculate_rto_charge,
    get_rates,
    validate_pincode,
)


TEST_CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "rate-calculator-tests",
    }
}


def rate_card_mock(**kwargs):
    mock = MagicMock()
    mock.base_weight = kwargs.get("base_weight", 0.5)
    mock.base_charge = kwargs.get("base_charge", 40)
    mock.additional_weight_slab = kwargs.get("additional_weight_slab", 0.5)
    mock.additional_charge = kwargs.get("additional_charge", 15)
    mock.cod_fixed_charge = kwargs.get("cod_fixed_charge", 20)
    mock.cod_percent = kwargs.get("cod_percent", 0)
    mock.rto_base_weight = kwargs.get("rto_base_weight", 0.5)
    mock.rto_base_charge = kwargs.get("rto_base_charge", 30)
    mock.rto_additional_weight_slab = kwargs.get("rto_additional_weight_slab", 0.5)
    mock.rto_additional_charge = kwargs.get("rto_additional_charge", 10)
    return mock


class ValidatePincodeTest(TestCase):
    def test_valid_pincode(self):
        validate_pincode("110001")

    def test_short_pincode_raises(self):
        with self.assertRaises(ValueError):
            validate_pincode("1100")

    def test_alpha_pincode_raises(self):
        with self.assertRaises(ValueError):
            validate_pincode("ABCDEF")


class RateMathTest(TestCase):
    @override_settings(GST_ON_SHIPMENT=0.18)
    def test_spec_formula(self):
        rate = calculate_rate_for_courier(rate_card_mock(), 1.2, "cod", 1500)
        self.assertEqual(rate["base"], 40)
        self.assertEqual(rate["additional"], 30)
        self.assertEqual(rate["cod"], 20)
        self.assertEqual(rate["gst"], 16.2)
        self.assertEqual(rate["total"], 106.2)

    def test_cod_percent_wins(self):
        rate = calculate_rate_for_courier(
            rate_card_mock(cod_fixed_charge=10, cod_percent=2.0),
            0.5,
            "cod",
            2000,
        )
        self.assertEqual(rate["cod"], 40.0)

    def test_prepaid_has_no_cod_charge(self):
        rate = calculate_rate_for_courier(rate_card_mock(), 0.5, "prepaid", 0)
        self.assertEqual(rate["cod"], 0)

    def test_rto_rate_calculation(self):
        rto_rate = calculate_rto_charge(rate_card_mock(), 1.2)
        self.assertEqual(rto_rate, {"base": 30, "additional": 20, "total": 50})

    @override_settings(GST_ON_SHIPMENT=0.10)
    def test_gst_uses_settings(self):
        rate = calculate_rate_for_courier(rate_card_mock(), 0.5, "prepaid", 0)
        self.assertEqual(rate["gst"], 4)
        self.assertEqual(rate["total"], 44)


@override_settings(CACHES=TEST_CACHES, GST_ON_SHIPMENT=0.18)
class GetRatesTest(TestCase):
    pickup = "110001"
    destination = "400001"

    def setUp(self):
        cache.clear()
        self.slow_cheap = self._courier("Slow Cheap", "SC", estimated_days=5)
        self.fast_expensive = self._courier(
            "Fast Expensive",
            "FE",
            base_charge=100,
            estimated_days=2,
        )
        self.no_rate_card = Courier.objects.create(name="No Rate", code="NR")
        self._serviceable(self.no_rate_card)

    def _courier(
        self,
        name,
        code,
        base_charge=40,
        additional_charge=15,
        estimated_days=3,
    ):
        courier = Courier.objects.create(name=name, code=code)
        self._serviceable(courier)
        RateCard.objects.create(
            courier=courier,
            zone="metro",
            service_type="surface",
            base_weight=0.5,
            base_charge=base_charge,
            additional_weight_slab=0.5,
            additional_charge=additional_charge,
            rto_base_weight=0.5,
            rto_base_charge=30,
            rto_additional_weight_slab=0.5,
            rto_additional_charge=10,
            cod_fixed_charge=20,
            cod_percent=1,
            estimated_days=estimated_days,
            is_active=True,
        )
        return courier

    def _serviceable(self, courier):
        CourierServiceability.objects.create(
            courier=courier,
            pin_code=self.pickup,
            is_pickup=True,
            is_delivery=False,
        )
        CourierServiceability.objects.create(
            courier=courier,
            pin_code=self.destination,
            is_pickup=False,
            is_delivery=True,
        )

    def test_cheapest_sort_and_response_shape(self):
        results = get_rates(
            pickup_pincode=self.pickup,
            destination_pincode=self.destination,
            weight_kg=1.2,
        )
        self.assertEqual([result["courier"] for result in results], ["Slow Cheap", "Fast Expensive"])
        self.assertNotIn("courier_code", results[0])
        self.assertNotIn("zone", results[0])
        self.assertEqual(results[0]["rto_rate"], {"base": 30, "additional": 20, "total": 50})
        self.assertEqual(set(results[0]["rate"].keys()), {"base", "additional", "cod", "gst", "total"})

    def test_fastest_sort(self):
        results = get_rates(
            pickup_pincode=self.pickup,
            destination_pincode=self.destination,
            weight_kg=0.5,
            sort_by="fastest",
        )
        self.assertEqual(results[0]["courier"], "Fast Expensive")

    def test_missing_rate_card_is_skipped(self):
        results = get_rates(
            pickup_pincode=self.pickup,
            destination_pincode=self.destination,
            weight_kg=0.5,
        )
        self.assertEqual(len(results), 2)
        self.assertNotIn("No Rate", [result["courier"] for result in results])

    def test_cache_key_includes_order_value(self):
        first = get_rates(
            pickup_pincode=self.pickup,
            destination_pincode=self.destination,
            weight_kg=0.5,
            payment_method="cod",
            order_value=100,
        )
        second = get_rates(
            pickup_pincode=self.pickup,
            destination_pincode=self.destination,
            weight_kg=0.5,
            payment_method="cod",
            order_value=10000,
        )
        self.assertEqual(first[0]["rate"]["cod"], 20)
        self.assertEqual(second[0]["rate"]["cod"], 100)
