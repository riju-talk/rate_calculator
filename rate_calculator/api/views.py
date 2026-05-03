import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from rate_calculator.services.rate_calculator import get_rates
from rate_calculator.api.serializers import CourierRateSerializer, RateRequestSerializer

logger = logging.getLogger(__name__)


class RateCalculatorView(APIView):
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
                sort_by=data.get("sort_by", "cheapest"),
            )
        except ValueError as exc:
            return Response(
                {
                    "success": False,
                    "message": str(exc),
                    "errors": {},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.error("Rate calculation error: %s", exc, exc_info=True)
            return Response(
                {
                    "success": False,
                    "message": "Failed to calculate rates. Please try again.",
                    "errors": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if not results:
            return Response(
                {
                    "success": False,
                    "message": (
                        "No couriers available for "
                        f"{data.get('pickup_pincode') or 'hub'} -> "
                        f"{data['destination_pincode']}. "
                        "Please try a different route or contact support."
                    ),
                    "errors": {},
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        output_serializer = CourierRateSerializer(results, many=True)
        return Response(
            {
                "success": True,
                "data": output_serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @staticmethod
    def _first_error(errors: dict) -> str:
        for field, messages in errors.items():
            message = messages[0] if isinstance(messages, list) else str(messages)
            if field == "non_field_errors":
                return str(message)
            return f"{field}: {message}"
        return "Invalid request."
