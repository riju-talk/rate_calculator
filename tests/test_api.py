"""
Integration tests for POST /api/rate-calculator/

These tests hit the full Django request-response cycle but mock the
service layer to keep tests fast and deterministic.
"""

import json
from unittest.mock import patch
from django.test import TestCase, Client
from django.urls import reverse


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
        "courier_id": 1,
        "courier_code": "XB",
        "service_type": "surface",
        "zone": "metro",
        "chargeable_weight": 1.2,
        "estimated_days": 3,
        "rate": {
            "base": 40.0,
            "additional": 30.0,
            "cod": 22.5,
            "gst": 16.65,
            "total": 109.15,
        },
    }
]


class RateCalculatorAPITest(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = "/api/rate-calculator/"

    # ── Happy path ────────────────────────────────────────────────────────

    @patch("shipping.api.views.get_rates", return_value=MOCK_RATE_RESULT)
    def test_successful_response(self, mock_get_rates):
        response = self.client.post(
            self.url,
            data=json.dumps(VALID_PAYLOAD),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["data"][0]["courier"], "XpressBees")

    @patch("shipping.api.views.get_rates", return_value=MOCK_RATE_RESULT)
    def test_hub_id_accepted(self, mock_get_rates):
        payload = {**VALID_PAYLOAD}
        del payload["pickup_pincode"]
        payload["hub_id"] = 1
        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

    # ── Validation errors ─────────────────────────────────────────────────

    def test_missing_source_returns_400(self):
        payload = {**VALID_PAYLOAD}
        del payload["pickup_pincode"]
        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])

    def test_invalid_destination_pincode_returns_400(self):
        payload = {**VALID_PAYLOAD, "destination_pincode": "ABC"}
        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_cod_without_order_value_returns_400(self):
        payload = {**VALID_PAYLOAD, "order_value": 0}
        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_negative_weight_returns_400(self):
        payload = {**VALID_PAYLOAD, "weight": -1}
        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_same_pickup_and_destination_returns_400(self):
        payload = {**VALID_PAYLOAD, "destination_pincode": "110001"}
        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    # ── Edge cases ────────────────────────────────────────────────────────

    @patch("shipping.api.views.get_rates", return_value=[])
    def test_no_couriers_returns_404(self, mock_get_rates):
        response = self.client.post(
            self.url,
            data=json.dumps(VALID_PAYLOAD),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.json()["success"])

    @patch("shipping.api.views.get_rates", side_effect=ValueError("Invalid hub"))
    def test_service_value_error_returns_400(self, mock_get_rates):
        response = self.client.post(
            self.url,
            data=json.dumps(VALID_PAYLOAD),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid hub", response.json()["message"])

    @patch("shipping.api.views.get_rates", side_effect=Exception("DB down"))
    def test_unexpected_exception_returns_500(self, mock_get_rates):
        response = self.client.post(
            self.url,
            data=json.dumps(VALID_PAYLOAD),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 500)
        self.assertFalse(response.json()["success"])
