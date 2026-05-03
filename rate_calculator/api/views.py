"""
views.py
--------
Rate Calculator API endpoint.

POST /api/rate-calculator/
    → validates input via RateRequestSerializer
    → delegates to services.get_rates()
    → returns sorted courier list with pricing
"""

import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from rate_calculator.services.rate_calculator import get_rates
from .serializers import RateRequestSerializer, CourierRateSerializer

logger = logging.getLogger(__name__)


class RateCalculatorView(APIView):
    """
    Calculate shipping rates for a given route and package.

    Request body (JSON):
        pickup_pincode OR hub_id  — origin (at least one required)
        destination_pincode       — 6-digit delivery pincode
        weight                    — dead weight in kg (required)
        length, width, height     — dimensions in cm (optional)
        payment_method            — 'cod' or 'prepaid' (default: prepaid)
        order_value               — required if payment_method == 'cod'

    Response:
        200 → { success: true, count: N, data: [...] }
        400 → { success: false, message: "...", errors: {...} }
        404 → { success: false, message: "No couriers available..." }
        500 → { success: false, message: "Unexpected error" }
    """

    def post(self, request):
        serializer = RateRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "message": self._first_error(serializer.errors),
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data

        try:
            results = get_rates(
                pickup_pincode=data.get("pickup_pincode"),
                hub_id=data.get("hub_id"),
                destination_pincode=data["destination_pincode"],
                weight_kg=data["weight"],
                length=data.get("length", 0),
                width=data.get("width", 0),
                height=data.get("height", 0),
                payment_method=data.get("payment_method", "prepaid"),
                order_value=data.get("order_value", 0),
            )

        except ValueError as exc:
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.error("Rate calculation error: %s", exc, exc_info=True)
            return Response(
                {
                    "success": False,
                    "message": "Failed to calculate rates. Please try again.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if not results:
            return Response(
                {
                    "success": False,
                    "message": (
                        f"No couriers available for "
                        f"{data.get('pickup_pincode') or 'hub'} → "
                        f"{data['destination_pincode']}. "
                        "Please try a different route or contact support."
                    ),
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Validate output shape (catches bugs in service layer during development)
        out_serializer = CourierRateSerializer(results, many=True)

        return Response(
            {
                "success": True,
                "count": len(results),
                "data": out_serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @staticmethod
    def _first_error(errors: dict) -> str:
        """Extract the first human-readable error from DRF's error dict."""
        for field, msgs in errors.items():
            msg = msgs[0] if isinstance(msgs, list) else str(msgs)
            if field == "non_field_errors":
                return str(msg)
            return f"{field}: {msg}"
        return "Invalid request."
