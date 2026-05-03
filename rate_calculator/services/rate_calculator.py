"""
rate_calculator.py
------------------
Orchestrates the full rate calculation pipeline:

    resolve pincode → validate → weight → zone → serviceability
    → fetch rate cards → calculate per-courier → sort → return

All public functions raise ValueError for bad inputs (caught in the view).
Results are cached in Redis to avoid repeated DB hits for the same route.
"""

import math
import logging
from typing import Optional

from django.conf import settings
from django.core.cache import cache

from rate_calculator.models import Hub, RateCard
from .weight_calculator import calculate_chargeable_weight
from .zone_resolver import resolve_zone
from .serviceability import get_serviceable_couriers

logger = logging.getLogger(__name__)

GST_RATE = getattr(settings, "GST_ON_SHIPMENT", 0.18)
RATE_CACHE_TTL = getattr(settings, "RATE_CACHE_TTL", 300)


# ─── Input helpers ────────────────────────────────────────────────────────────

def resolve_pickup_pincode(
    pickup_pincode: Optional[str] = None,
    hub_id: Optional[int] = None,
) -> str:
    """
    Returns the origin pincode string.
    Prefers hub_id → looks up Hub.pin_code from DB.
    Falls back to pickup_pincode if hub_id not given.
    """
    if hub_id is not None:
        try:
            hub = Hub.objects.get(id=hub_id, is_active=True)
            return hub.pin_code
        except Hub.DoesNotExist:
            raise ValueError(f"Hub with id={hub_id} not found or inactive.")

    if pickup_pincode:
        return pickup_pincode

    raise ValueError("Either pickup_pincode or hub_id must be provided.")


def validate_pincode(pincode: str, field_name: str = "pincode") -> None:
    """Raises ValueError if pincode is not exactly 6 digits."""
    if not isinstance(pincode, str) or not pincode.isdigit() or len(pincode) != 6:
        raise ValueError(f"'{field_name}' must be a 6-digit numeric string, got: '{pincode}'.")


# ─── Charge components ────────────────────────────────────────────────────────

def _calculate_cod_charge(rate_card: RateCard, order_value: float) -> float:
    """
    COD charge = max(fixed_charge, percent_of_order_value).
    If both are 0, returns 0 (COD is free for that courier).
    """
    fixed = rate_card.cod_fixed_charge
    percent_based = (rate_card.cod_percent / 100.0) * order_value if order_value > 0 else 0.0
    return max(fixed, percent_based)


def _calculate_rto_charge(rate_card: RateCard, chargeable_weight: float) -> dict:
    """
    RTO (Return To Origin) charge breakdown for a single rate card.

    Formula:
        extra_weight = max(0, chargeable_weight - rto_base_weight)
        slabs        = ceil(extra_weight / rto_additional_weight_slab)
        additional   = slabs × rto_additional_charge
        total_rto    = rto_base_charge + additional
    """
    extra_weight = max(0.0, chargeable_weight - rate_card.rto_base_weight)
    slabs = math.ceil(extra_weight / rate_card.rto_additional_weight_slab) if extra_weight > 0 else 0

    base = rate_card.rto_base_charge
    additional = slabs * rate_card.rto_additional_charge
    return {"base": round(base, 2), "additional": round(additional, 2)}


def _calculate_forward_charge(rate_card: RateCard, chargeable_weight: float) -> dict:
    """
    Forward charge breakdown for a single rate card.

    Formula:
        extra_weight = max(0, chargeable_weight - base_weight)
        slabs        = ceil(extra_weight / additional_weight_slab)
        additional   = slabs × additional_charge
        total_fwd    = base_charge + additional
    """
    extra_weight = max(0.0, chargeable_weight - rate_card.base_weight)
    slabs = math.ceil(extra_weight / rate_card.additional_weight_slab) if extra_weight > 0 else 0

    base = rate_card.base_charge
    additional = slabs * rate_card.additional_charge
    return {"base": round(base, 2), "additional": round(additional, 2)}


def calculate_rate_for_courier(
    rate_card: RateCard,
    chargeable_weight: float,
    payment_method: str,
    order_value: float,
) -> dict:
    """
    Full rate breakdown for one courier + rate card.

    Returns:
        {
            "base": float,
            "additional": float,
            "cod": float,
            "rto": float,
            "gst": float,
            "total": float,
        }
    """
    fwd = _calculate_forward_charge(rate_card, chargeable_weight)
    rto = _calculate_rto_charge(rate_card, chargeable_weight)
    cod = (
        _calculate_cod_charge(rate_card, order_value)
        if payment_method == "cod"
        else 0.0
    )

    subtotal = fwd["base"] + fwd["additional"] + rto["base"] + rto["additional"] + cod
    gst = round(subtotal * GST_RATE, 2)
    total = round(subtotal + gst, 2)

    return {
        "base": fwd["base"],
        "additional": fwd["additional"],
        "cod": round(cod, 2),
        "rto": round(rto["base"] + rto["additional"], 2),
        "gst": gst,
        "total": total,
    }


# ─── Main public API ──────────────────────────────────────────────────────────

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
) -> list[dict]:
    """
    Full rate calculation pipeline. Returns a list of courier rate dicts,
    sorted cheapest-first.

    Pipeline:
        1. Resolve origin pincode (hub or direct)
        2. Validate both pincodes
        3. Compute chargeable weight
        4. Determine shipping zone
        5. Check serviceability
        6. Fetch & apply rate cards
        7. Sort by total price
        8. Cache result

    Args:
        destination_pincode : 6-digit delivery pincode
        weight_kg           : Dead weight in kg
        pickup_pincode      : Origin pincode (optional if hub_id given)
        hub_id              : Hub PK (optional if pickup_pincode given)
        length/width/height : Package dimensions in cm (optional)
        payment_method      : 'cod' or 'prepaid'
        order_value         : Required for COD charge calculation

    Returns:
        List of dicts, each containing courier name, pricing breakdown,
        zone, chargeable_weight, and estimated_days.

    Raises:
        ValueError: On invalid input (bad pincode, missing hub, etc.)
    """

    # ── Step 1: Resolve origin pincode ────────────────────────────────────
    origin_pincode = resolve_pickup_pincode(pickup_pincode, hub_id)

    # ── Step 2: Validate pincodes ─────────────────────────────────────────
    validate_pincode(origin_pincode, "pickup_pincode")
    validate_pincode(destination_pincode, "destination_pincode")

    # ── Step 3: Chargeable weight ─────────────────────────────────────────
    chargeable_weight = calculate_chargeable_weight(weight_kg, length, width, height)

    # ── Step 4: Zone ──────────────────────────────────────────────────────
    zone = resolve_zone(origin_pincode, destination_pincode)

    # ── Cache key ─────────────────────────────────────────────────────────
    cache_key = (
        f"rates:{origin_pincode}:{destination_pincode}:"
        f"{chargeable_weight}:{zone}:{payment_method}:{order_value}"
    )
    cached = cache.get(cache_key)
    if cached is not None:
        logger.debug("Cache hit for key: %s", cache_key)
        return cached

    # ── Step 5: Serviceable couriers ──────────────────────────────────────
    serviceable_couriers = get_serviceable_couriers(
        origin_pincode, destination_pincode, payment_method
    )
    serviceable_ids = list(serviceable_couriers.values_list("id", flat=True))

    if not serviceable_ids:
        logger.info(
            "No serviceable couriers for %s → %s", origin_pincode, destination_pincode
        )
        return []

    # ── Step 6: Fetch rate cards (single query, no N+1) ───────────────────
    rate_cards = (
        RateCard.objects
        .select_related("courier")
        .filter(
            zone=zone,
            is_active=True,
            courier_id__in=serviceable_ids,
            courier__is_active=True,
        )
    )

    results = []
    for rc in rate_cards:
        try:
            rate = calculate_rate_for_courier(rc, chargeable_weight, payment_method, order_value)
            results.append(
                {
                    "courier": rc.courier.name,
                    "courier_id": rc.courier.id,
                    "courier_code": rc.courier.code,
                    "service_type": rc.service_type,
                    "zone": zone,
                    "chargeable_weight": chargeable_weight,
                    "estimated_days": rc.estimated_days,
                    "rate": rate,
                }
            )
        except Exception as exc:
            # Log but don't crash the whole response for one bad rate card
            logger.error(
                "Rate calculation failed for courier=%s zone=%s: %s",
                rc.courier.name, zone, exc,
                exc_info=True,
            )

    # ── Step 7: Sort cheapest first ───────────────────────────────────────
    results.sort(key=lambda x: x["rate"]["total"])

    # ── Step 8: Cache ─────────────────────────────────────────────────────
    cache.set(cache_key, results, RATE_CACHE_TTL)
    logger.info(
        "Calculated rates: %d couriers | %s→%s | zone=%s | weight=%.2fkg",
        len(results), origin_pincode, destination_pincode, zone, chargeable_weight,
    )

    return results
