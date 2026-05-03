from django.contrib import admin
from shipping.models import Hub, Courier, CourierServiceability, ZoneMapping, RateCard


@admin.register(Hub)
class HubAdmin(admin.ModelAdmin):
    list_display = ("name", "pin_code", "city", "state", "is_active")
    list_filter = ("is_active", "state")
    search_fields = ("name", "pin_code", "city")
    ordering = ("name",)


class CourierServiceabilityInline(admin.TabularInline):
    model = CourierServiceability
    extra = 1
    fields = ("pin_code", "is_pickup", "is_delivery")


@admin.register(Courier)
class CourierAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "supports_cod", "is_active")
    list_filter = ("is_active", "supports_cod")
    search_fields = ("name", "code")
    inlines = [CourierServiceabilityInline]


@admin.register(CourierServiceability)
class CourierServiceabilityAdmin(admin.ModelAdmin):
    list_display = ("courier", "pin_code", "is_pickup", "is_delivery")
    list_filter = ("is_pickup", "is_delivery", "courier")
    search_fields = ("pin_code", "courier__name")


@admin.register(ZoneMapping)
class ZoneMappingAdmin(admin.ModelAdmin):
    list_display = ("origin_prefix", "destination_prefix", "zone")
    list_filter = ("zone",)
    search_fields = ("origin_prefix", "destination_prefix")


@admin.register(RateCard)
class RateCardAdmin(admin.ModelAdmin):
    list_display = (
        "courier", "zone", "service_type",
        "base_charge", "additional_charge",
        "cod_fixed_charge", "cod_percent",
        "estimated_days", "is_active",
    )
    list_filter = ("zone", "service_type", "is_active", "courier")
    search_fields = ("courier__name",)
    ordering = ("courier__name", "zone")