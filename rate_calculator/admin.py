from django.contrib import admin

from rate_calculator.models import (
    Courier,
    CourierServiceability,
    Hub,
    RateCard,
    ZoneMapping,
)


@admin.register(Hub)
class HubAdmin(admin.ModelAdmin):
    list_display = ("name", "pin_code", "city", "state", "is_active")
    list_filter = ("is_active", "state")
    search_fields = ("name", "pin_code", "city")


@admin.register(Courier)
class CourierAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active", "supports_cod")
    list_filter = ("is_active", "supports_cod")
    search_fields = ("name", "code")


@admin.register(CourierServiceability)
class CourierServiceabilityAdmin(admin.ModelAdmin):
    list_display = ("courier", "pin_code", "is_pickup", "is_delivery")
    list_filter = ("is_pickup", "is_delivery", "courier")
    search_fields = ("courier__name", "courier__code", "pin_code")


@admin.register(ZoneMapping)
class ZoneMappingAdmin(admin.ModelAdmin):
    list_display = ("origin_prefix", "destination_prefix", "zone")
    list_filter = ("zone",)
    search_fields = ("origin_prefix", "destination_prefix")


@admin.register(RateCard)
class RateCardAdmin(admin.ModelAdmin):
    list_display = (
        "courier",
        "zone",
        "service_type",
        "base_charge",
        "additional_charge",
        "estimated_days",
        "is_active",
    )
    list_filter = ("zone", "service_type", "is_active", "courier")
    search_fields = ("courier__name", "courier__code")
