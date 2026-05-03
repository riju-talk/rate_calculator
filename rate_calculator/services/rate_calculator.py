import logging
import math
from typing import Optional

from django.conf import settings
from django.core.cache import cache

from rate_calculator.models import Hub, RateCard
from rate_calculator.services.serviceability import get_serviceable_couriers
from rate_calculator.services.weight_calculator import calculate_chargeable_weight
from rate_calculator.services.zone_resolver import resolve_zone

logger = logging.getLogger(__name__)

PAYMENT_METHODS = {"cod", "prepaid"}
SORT_OPTIONS = {"cheapest", "fastest"}


def resolve_pickup_pincode(
    pickup_pincode: Optional[str] = None,
    hub_id: Optional[int] = None,
) -> str:
    if hub_id is not None:
        try:
            hub = Hub.objects.only("pin_code").get(id=hub_id, is_active=True)
        except Hub.DoesNotExist as exc:
            raise ValueError(f"Hub with id={hub_id} not found or inactive.") from exc
        return hub.pin_code

    if pickup_pincode:
        return pickup_pincode

    raise ValueError("Either pickup_pincode or hub_id must be provided.")


def validate_pincode(pincode: str, field_name: str = "pincode") -> None:
    if not isinstance(pincode, str) or not pincode.isdigit() or len(pincode) != 6:
        raise ValueError(
            f"'{field_name}' must be a 6-digit numeric string, got: '{pincode}'."
        )


def _validate_numeric_inputs(
    weight_kg: float,
    length: float,
    width: float,
    height: float,
    payment_method: str,
    order_value: float,
    sort_by: str,
) -> None:
    if weight_kg <= 0:
        raise ValueError("weight must be greater than 0.")

    if length < 0 or width < 0 or height < 0:
        raise ValueError("length, width, and height must be greater than or equal to 0.")

    if payment_method not in PAYMENT_METHODS:
        raise ValueError("payment_method must be either 'cod' or 'prepaid'.")

    if payment_method == "cod" and order_value <= 0:
        raise ValueError("order_value is required and must be greater than 0 for COD.")

    if sort_by not in SORT_OPTIONS:
        raise ValueError("sort_by must be either 'cheapest' or 'fastest'.")


def calculate_cod_charge(rate_card: RateCard, order_value: float) -> float:
    fixed = rate_card.cod_fixed_charge
    percent_based = order_value * rate_card.cod_percent / 100
    return max(fixed, percent_based)


def calculate_forward_charge(rate_card: RateCard, chargeable_weight: float) -> dict:
    extra_weight = max(0.0, chargeable_weight - rate_card.base_weight)
    slabs = (
        math.ceil(extra_weight / rate_card.additional_weight_slab)
        if extra_weight > 0
        else 0
    )
    base = round(rate_card.base_charge, 2)
    additional = round(slabs * rate_card.additional_charge, 2)
    return {"base": base, "additional": additional}


def calculate_rto_charge(rate_card: RateCard, chargeable_weight: float) -> dict:
    extra_weight = max(0.0, chargeable_weight - rate_card.rto_base_weight)
    slabs = (
        math.ceil(extra_weight / rate_card.rto_additional_weight_slab)
        if extra_weight > 0
        else 0
    )
    base = round(rate_card.rto_base_charge, 2)
    additional = round(slabs * rate_card.rto_additional_charge, 2)
    return {
        "base": base,
        "additional": additional,
        "total": round(base + additional, 2),
    }


def calculate_rate_for_courier(
    rate_card: RateCard,
    chargeable_weight: float,
    payment_method: str,
    order_value: float,
) -> dict:
    forward = calculate_forward_charge(rate_card, chargeable_weight)
    cod = (
        calculate_cod_charge(rate_card, order_value)
        if payment_method == "cod"
        else 0.0
    )

    subtotal = forward["base"] + forward["additional"] + cod
    gst_rate = getattr(settings, "GST_ON_SHIPMENT", 0.18)
    gst = round(subtotal * gst_rate, 2)
    total = round(subtotal + gst, 2)

    return {
        "base": forward["base"],
        "additional": forward["additional"],
        "cod": round(cod, 2),
        "gst": gst,
        "total": total,
    }


def _build_cache_key(
    origin_pincode: str,
    destination_pincode: str,
    chargeable_weight: float,
    zone: str,
    payment_method: str,
    order_value: float,
    sort_by: str,
) -> str:
    return (
        "rates:v1:"
        f"{origin_pincode}:{destination_pincode}:"
        f"{chargeable_weight:.3f}:{zone}:{payment_method}:"
        f"{order_value:.2f}:{sort_by}"
    )


def _sort_results(results: list[dict], sort_by: str) -> list[dict]:
    if sort_by == "fastest":
        return sorted(results, key=lambda item: (item["estimated_days"], item["rate"]["total"]))
    return sorted(results, key=lambda item: (item["rate"]["total"], item["estimated_days"]))


def get_rates(
    destination_pincode: str,
    weight_kg: float,
    pickup_pincode: Optional[str] = None,
    hub_id: Optional[int] = None,
    length: float = 0.0,
    width: float = 0.0,
    height: float = 0.0,
    payment_method: str = "prepaid",
    order_value: float = 0.0,
    sort_by: str = "cheapest",
) -> list[dict]:
    _validate_numeric_inputs(
        weight_kg,
        length,
        width,
        height,
        payment_method,
        order_value,
        sort_by,
    )

    origin_pincode = resolve_pickup_pincode(pickup_pincode, hub_id)

    validate_pincode(origin_pincode, "pickup_pincode")
    validate_pincode(destination_pincode, "destination_pincode")

    serviceable_couriers = list(
        get_serviceable_couriers(origin_pincode, destination_pincode, payment_method)
    )
    if not serviceable_couriers:
        logger.info(
            "No serviceable couriers for %s -> %s",
            origin_pincode,
            destination_pincode,
        )
        return []

    chargeable_weight = calculate_chargeable_weight(
        weight_kg,
        length,
        width,
        height,
    )
    zone = resolve_zone(origin_pincode, destination_pincode)

    cache_key = _build_cache_key(
        origin_pincode,
        destination_pincode,
        chargeable_weight,
        zone,
        payment_method,
        order_value,
        sort_by,
    )
    cached = cache.get(cache_key)
    if cached is not None:
        logger.debug("Cache hit for key: %s", cache_key)
        return cached

    serviceable_ids = [courier.id for courier in serviceable_couriers]
    rate_cards = (
        RateCard.objects.select_related("courier")
        .filter(
            zone=zone,
            is_active=True,
            courier_id__in=serviceable_ids,
            courier__is_active=True,
        )
        .order_by("courier__name", "service_type")
    )

    results = []
    for rate_card in rate_cards:
        try:
            rate = calculate_rate_for_courier(
                rate_card,
                chargeable_weight,
                payment_method,
                order_value,
            )
            rto_rate = calculate_rto_charge(rate_card, chargeable_weight)
            results.append(
                {
                    "courier": rate_card.courier.name,
                    "courier_id": rate_card.courier.id,
                    "service_type": rate_card.service_type,
                    "chargeable_weight": chargeable_weight,
                    "estimated_days": rate_card.estimated_days,
                    "rate": rate,
                    "rto_rate": rto_rate,
                }
            )
        except Exception as exc:
            logger.error(
                "Rate calculation failed for courier=%s zone=%s: %s",
                rate_card.courier.name,
                zone,
                exc,
                exc_info=True,
            )

    results = _sort_results(results, sort_by)
    cache.set(cache_key, results, getattr(settings, "RATE_CACHE_TTL", 300))

    logger.info(
        "Calculated rates: %d couriers | %s -> %s | zone=%s | weight=%.2fkg",
        len(results),
        origin_pincode,
        destination_pincode,
        zone,
        chargeable_weight,
    )
    return results


_calculate_cod_charge = calculate_cod_charge
_calculate_forward_charge = calculate_forward_charge
_calculate_rto_charge = calculate_rto_charge
