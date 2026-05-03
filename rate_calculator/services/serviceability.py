from django.db.models import Exists, OuterRef, Prefetch, QuerySet

from rate_calculator.models import Courier, CourierServiceability


def get_serviceable_couriers(
    pickup_pincode: str,
    destination_pincode: str,
    payment_method: str = "prepaid",
) -> QuerySet:
    pickup_match = CourierServiceability.objects.filter(
        courier_id=OuterRef("pk"),
        pin_code=pickup_pincode,
        is_pickup=True,
    )
    delivery_match = CourierServiceability.objects.filter(
        courier_id=OuterRef("pk"),
        pin_code=destination_pincode,
        is_delivery=True,
    )
    route_records = CourierServiceability.objects.filter(
        pin_code__in=[pickup_pincode, destination_pincode],
    )

    queryset = (
        Courier.objects.filter(is_active=True)
        .annotate(
            can_pickup=Exists(pickup_match),
            can_deliver=Exists(delivery_match),
        )
        .filter(can_pickup=True, can_deliver=True)
        .prefetch_related(
            Prefetch("serviceability_records", queryset=route_records),
        )
    )

    if payment_method == "cod":
        queryset = queryset.filter(supports_cod=True)

    return queryset
