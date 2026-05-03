from rate_calculator.models import ZoneMapping

SPECIAL_PREFIXES = {
    "785",
    "786",
    "787",
    "788",
    "791",
    "792",
    "795",
    "793",
    "796",
    "797",
    "737",
    "799",
    "744",
    "180",
    "181",
    "182",
    "190",
    "191",
    "192",
    "193",
    "194",
}

METRO_PREFIXES = {"110", "400", "600", "700", "500", "560", "380", "411"}


def resolve_zone(pickup_pincode: str, destination_pincode: str) -> str:
    origin_3 = pickup_pincode[:3]
    dest_3 = destination_pincode[:3]

    if origin_3 in SPECIAL_PREFIXES or dest_3 in SPECIAL_PREFIXES:
        return "special"

    mapping = ZoneMapping.objects.filter(
        origin_prefix=origin_3,
        destination_prefix=dest_3,
    ).first()
    if mapping:
        return mapping.zone

    mapping = ZoneMapping.objects.filter(
        origin_prefix=pickup_pincode[:2],
        destination_prefix=destination_pincode[:2],
    ).first()
    if mapping:
        return mapping.zone

    if origin_3 == dest_3:
        return "local"

    if pickup_pincode[:2] == destination_pincode[:2]:
        return "state"

    if origin_3 in METRO_PREFIXES and dest_3 in METRO_PREFIXES:
        return "metro"

    return "roi"
