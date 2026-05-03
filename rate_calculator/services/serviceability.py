"""
serviceability.py
-----------------
Checks which couriers can serve a given pickup → delivery pincode pair.

A courier is considered serviceable for a route when:
    - It has a serviceability record for the pickup pincode (is_pickup=True)
    - It has a serviceability record for the destination pincode (is_delivery=True)
    - It is marked is_active=True

Returns a queryset of Courier objects that meet these criteria.
"""

from django.db.models import QuerySet
from rate_calculator.models import Courier, CourierServiceability


def get_serviceable_couriers(
    pickup_pincode: str,
    destination_pincode: str,
    payment_method: str = "prepaid",
) -> QuerySet:
    """
    Returns active couriers that can serve the pickup → destination route.

    Filters:
        - Courier is_active
        - Has a pickup serviceability record for pickup_pincode
        - Has a delivery serviceability record for destination_pincode
        - If payment_method is 'cod', courier must support COD

    Uses subqueries to avoid N+1 — single DB round-trip.
    """
    # Courier IDs that can pick up from origin
    pickup_courier_ids = CourierServiceability.objects.filter(
        pin_code=pickup_pincode, is_pickup=True
    ).values_list("courier_id", flat=True)

    # Courier IDs that can deliver to destination
    delivery_courier_ids = CourierServiceability.objects.filter(
        pin_code=destination_pincode, is_delivery=True
    ).values_list("courier_id", flat=True)

    qs = Courier.objects.filter(
        id__in=pickup_courier_ids,
        is_active=True,
    ).filter(id__in=delivery_courier_ids)

    if payment_method == "cod":
        qs = qs.filter(supports_cod=True)

    return qs
