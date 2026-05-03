"""
zone_resolver.py
----------------
Determines the shipping zone for a pickup → destination pincode pair.

Resolution order (first match wins):
    1. Special zone  — hardcoded North East / J&K prefix list
    2. DB lookup     — ZoneMapping table (most flexible, ops-managed)
    3. Heuristics    — local / state / metro / roi fallback

Keeping the hardcoded list short; prefer populating ZoneMapping for accuracy.
"""

from shipping.models import ZoneMapping

# Special pincodes by 3-digit prefix (more accurate than 2-digit)
# North East states, J&K, Andaman, Lakshadweep
SPECIAL_PINCODE_PREFIXES = {
    # Assam
    "781", "782", "783", "784", "785", "786", "787", "788",
    # Nagaland
    "797",
    # Manipur
    "795",
    # Mizoram
    "796",
    # Tripura
    "799",
    # Meghalaya
    "793", "794",
    # Arunachal Pradesh
    "790", "791", "792",
    # Sikkim
    "737",
    # Andaman & Nicobar
    "744",
    # Lakshadweep
    "682",  # Lakshadweep shares prefix with Ernakulam — keep as DB override
    # J&K / Ladakh
    "190", "191", "192", "193", "194",
    # Himachal Pradesh border areas
    "176", "177",
}

# Major metro pincode 3-digit prefixes
METRO_PREFIXES = {
    "110",  # Delhi / NCR
    "400", "401",  # Mumbai
    "600",  # Chennai
    "700",  # Kolkata
    "500", "501",  # Hyderabad
    "560",  # Bangalore
    "380", "382",  # Ahmedabad
    "411", "412",  # Pune
}


def resolve_zone(pickup_pincode: str, destination_pincode: str) -> str:
    """
    Determine the shipping zone for a pickup → destination route.

    Args:
        pickup_pincode: 6-digit origin pincode string.
        destination_pincode: 6-digit destination pincode string.

    Returns:
        Zone string: one of 'local', 'state', 'metro', 'roi', 'special'.
    """
    # ── 1. Special zone check (3-digit prefix on destination) ─────────────
    if destination_pincode[:3] in SPECIAL_PINCODE_PREFIXES:
        return "special"

    # ── 2. DB lookup (3-char prefix first, then 2-char fallback) ─────────
    origin_3 = pickup_pincode[:3]
    dest_3 = destination_pincode[:3]

    mapping = ZoneMapping.objects.filter(
        origin_prefix=origin_3, destination_prefix=dest_3
    ).first()

    if not mapping:
        # Try 2-digit state-level prefix
        mapping = ZoneMapping.objects.filter(
            origin_prefix=pickup_pincode[:2],
            destination_prefix=destination_pincode[:2],
        ).first()

    if mapping:
        return mapping.zone

    # ── 3. Heuristic fallback ─────────────────────────────────────────────
    if origin_3 == dest_3:
        return "local"

    if pickup_pincode[:2] == destination_pincode[:2]:
        return "state"

    if origin_3 in METRO_PREFIXES and dest_3 in METRO_PREFIXES:
        return "metro"

    return "roi"