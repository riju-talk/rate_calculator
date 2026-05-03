"""
serializers.py
--------------
Input validation and output shaping for the Rate Calculator API.
"""

from rest_framework import serializers


# ─── Request ──────────────────────────────────────────────────────────────────

class RateRequestSerializer(serializers.Serializer):
    """
    Validates the incoming POST body for /api/rate-calculator/.

    Rules enforced here (beyond field-level):
        - pickup_pincode OR hub_id must be present (not both required, but at least one).
        - If payment_method is 'cod', order_value must be > 0.
        - All dimension fields must be >= 0.
        - weight must be > 0.
    """

    # Source location — one of these is required
    pickup_pincode = serializers.CharField(max_length=6, required=False, allow_blank=False)
    hub_id = serializers.IntegerField(min_value=1, required=False)

    # Destination
    destination_pincode = serializers.CharField(max_length=6)

    # Package
    weight = serializers.FloatField(min_value=0.001)
    length = serializers.FloatField(min_value=0, required=False, default=0)
    width = serializers.FloatField(min_value=0, required=False, default=0)
    height = serializers.FloatField(min_value=0, required=False, default=0)

    # Payment
    payment_method = serializers.ChoiceField(
        choices=["cod", "prepaid"],
        default="prepaid",
        required=False,
    )
    order_value = serializers.FloatField(min_value=0, required=False, default=0)

    # ── Field-level validation ────────────────────────────────────────────

    def validate_pickup_pincode(self, value: str) -> str:
        if value and (not value.isdigit() or len(value) != 6):
            raise serializers.ValidationError("Must be exactly 6 digits.")
        return value

    def validate_destination_pincode(self, value: str) -> str:
        if not value.isdigit() or len(value) != 6:
            raise serializers.ValidationError("Must be exactly 6 digits.")
        return value

    # ── Cross-field validation ────────────────────────────────────────────

    def validate(self, data: dict) -> dict:
        # Source location check
        if not data.get("pickup_pincode") and not data.get("hub_id"):
            raise serializers.ValidationError(
                "Either 'pickup_pincode' or 'hub_id' is required."
            )

        # Same origin and destination
        if (
            data.get("pickup_pincode")
            and data.get("destination_pincode") == data["pickup_pincode"]
        ):
            raise serializers.ValidationError(
                "pickup_pincode and destination_pincode cannot be the same."
            )

        # COD requires order_value
        if data.get("payment_method") == "cod" and not data.get("order_value"):
            raise serializers.ValidationError(
                "'order_value' is required and must be > 0 for COD shipments."
            )

        return data


# ─── Response ─────────────────────────────────────────────────────────────────

class RateBreakdownSerializer(serializers.Serializer):
    base = serializers.FloatField()
    additional = serializers.FloatField()
    cod = serializers.FloatField()
    rto = serializers.FloatField(required=False, default=0.0)
    gst = serializers.FloatField()
    total = serializers.FloatField()


class CourierRateSerializer(serializers.Serializer):
    courier = serializers.CharField()
    courier_id = serializers.IntegerField()
    courier_code = serializers.CharField()
    service_type = serializers.CharField()
    zone = serializers.CharField()
    chargeable_weight = serializers.FloatField()
    estimated_days = serializers.IntegerField()
    rate = RateBreakdownSerializer()
