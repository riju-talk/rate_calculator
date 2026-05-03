from rest_framework import serializers


class RateRequestSerializer(serializers.Serializer):
    pickup_pincode = serializers.CharField(
        max_length=6,
        required=False,
        allow_blank=False,
    )
    hub_id = serializers.IntegerField(min_value=1, required=False)

    destination_pincode = serializers.CharField(max_length=6)

    weight = serializers.FloatField(min_value=0.001)
    length = serializers.FloatField(min_value=0, required=False, default=0)
    width = serializers.FloatField(min_value=0, required=False, default=0)
    height = serializers.FloatField(min_value=0, required=False, default=0)

    payment_method = serializers.ChoiceField(
        choices=["cod", "prepaid"],
        default="prepaid",
        required=False,
    )
    order_value = serializers.FloatField(min_value=0, required=False, default=0)
    sort_by = serializers.ChoiceField(
        choices=["cheapest", "fastest"],
        default="cheapest",
        required=False,
    )

    def validate_pickup_pincode(self, value: str) -> str:
        if value and (not value.isdigit() or len(value) != 6):
            raise serializers.ValidationError("Must be exactly 6 digits.")
        return value

    def validate_destination_pincode(self, value: str) -> str:
        if not value.isdigit() or len(value) != 6:
            raise serializers.ValidationError("Must be exactly 6 digits.")
        return value

    def validate(self, data: dict) -> dict:
        if not data.get("pickup_pincode") and not data.get("hub_id"):
            raise serializers.ValidationError(
                "Either 'pickup_pincode' or 'hub_id' is required."
            )

        if (
            data.get("pickup_pincode")
            and data.get("destination_pincode") == data["pickup_pincode"]
        ):
            raise serializers.ValidationError(
                "pickup_pincode and destination_pincode cannot be the same."
            )

        if data.get("payment_method") == "cod" and data.get("order_value", 0) <= 0:
            raise serializers.ValidationError(
                "'order_value' is required and must be > 0 for COD shipments."
            )

        return data


class RateBreakdownSerializer(serializers.Serializer):
    base = serializers.FloatField()
    additional = serializers.FloatField()
    cod = serializers.FloatField()
    gst = serializers.FloatField()
    total = serializers.FloatField()


class RtoRateSerializer(serializers.Serializer):
    base = serializers.FloatField()
    additional = serializers.FloatField()
    total = serializers.FloatField()


class CourierRateSerializer(serializers.Serializer):
    courier = serializers.CharField()
    courier_id = serializers.IntegerField()
    service_type = serializers.CharField()
    chargeable_weight = serializers.FloatField()
    estimated_days = serializers.IntegerField()
    rate = RateBreakdownSerializer()
    rto_rate = RtoRateSerializer()
