import json
from unittest.mock import patch

from django.test import Client, TestCase, override_settings

VALID_PAYLOAD = {
    "pickup_pincode": "110001",
    "destination_pincode": "400001",
    "weight": 1.2,
    "length": 20,
    "width": 15,
    "height": 10,
    "payment_method": "cod",
    "order_value": 1500,
}

MOCK_RATE_RESULT = [
    {
        "courier": "XpressBees",
        "courier_id": 12,
        "service_type": "surface",
        "chargeable_weight": 1.5,
        "estimated_days": 3,
        "rate": {
            "base": 40,
            "additional": 30,
            "cod": 20,
            "gst": 16.2,
            "total": 106.2,
        },
        "rto_rate": {
            "base": 30,
            "additional": 20,
            "total": 50,
        },
    }
]

TEST_CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "rate-calculator-api-tests",
    }
}


@override_settings(CACHES=TEST_CACHES)
class RateCalculatorAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = "/api/rate-calculator/"

    def post(self, payload):
        return self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

    @patch("rate_calculator.api.views.get_rates", return_value=MOCK_RATE_RESULT)
    def test_success_response(self, mock_get_rates):
        response = self.post(VALID_PAYLOAD)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(set(body.keys()), {"success", "data"})
        self.assertTrue(body["success"])
        self.assertEqual(body["data"][0]["courier"], "XpressBees")
        mock_get_rates.assert_called_once()

    @patch("rate_calculator.api.views.get_rates", return_value=MOCK_RATE_RESULT)
    def test_response_shape(self, mock_get_rates):
        body = self.post(VALID_PAYLOAD).json()
        result = body["data"][0]
        self.assertNotIn("count", body)
        self.assertNotIn("courier_code", result)
        self.assertNotIn("zone", result)
        self.assertIn("rto_rate", result)
        self.assertEqual(set(result["rate"].keys()), {"base", "additional", "cod", "gst", "total"})
        self.assertEqual(set(result["rto_rate"].keys()), {"base", "additional", "total"})

    @patch("rate_calculator.api.views.get_rates", return_value=MOCK_RATE_RESULT)
    def test_hub_id_accepted(self, mock_get_rates):
        payload = {**VALID_PAYLOAD, "hub_id": 1}
        del payload["pickup_pincode"]
        self.assertEqual(self.post(payload).status_code, 200)

    @patch("rate_calculator.api.views.get_rates", return_value=MOCK_RATE_RESULT)
    def test_sort_fastest_passed_to_service(self, mock_get_rates):
        payload = {**VALID_PAYLOAD, "sort_by": "fastest"}
        response = self.post(payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_get_rates.call_args.kwargs["sort_by"], "fastest")

    def test_missing_source_returns_400(self):
        payload = {**VALID_PAYLOAD}
        del payload["pickup_pincode"]
        response = self.post(payload)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])
        self.assertIn("errors", response.json())

    def test_invalid_destination_pincode_returns_400(self):
        response = self.post({**VALID_PAYLOAD, "destination_pincode": "ABC"})
        self.assertEqual(response.status_code, 400)

    def test_cod_without_order_value_returns_400(self):
        response = self.post({**VALID_PAYLOAD, "order_value": 0})
        self.assertEqual(response.status_code, 400)

    def test_negative_weight_returns_400(self):
        response = self.post({**VALID_PAYLOAD, "weight": -1})
        self.assertEqual(response.status_code, 400)

    def test_same_pickup_and_destination_returns_400(self):
        response = self.post({**VALID_PAYLOAD, "destination_pincode": "110001"})
        self.assertEqual(response.status_code, 400)

    def test_invalid_sort_by_returns_400(self):
        response = self.post({**VALID_PAYLOAD, "sort_by": "slowest"})
        self.assertEqual(response.status_code, 400)

    @patch("rate_calculator.api.views.get_rates", return_value=[])
    def test_no_couriers_returns_404(self, mock_get_rates):
        response = self.post(VALID_PAYLOAD)
        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.json()["success"])
        self.assertEqual(response.json()["errors"], {})

    @patch("rate_calculator.api.views.get_rates", side_effect=ValueError("bad hub"))
    def test_value_error_returns_400(self, mock_get_rates):
        response = self.post(VALID_PAYLOAD)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["errors"], {})

    @patch("rate_calculator.api.views.get_rates", side_effect=Exception("crash"))
    def test_unexpected_error_returns_500(self, mock_get_rates):
        response = self.post(VALID_PAYLOAD)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["errors"], {})
