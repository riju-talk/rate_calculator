from django.db import models


class Courier(models.Model):
    """
    A courier partner (e.g. XpressBees, Delhivery, DTDC).
    Stores serviceability and COD capability metadata.
    Pincode-level serviceability is handled via CourierServiceability.
    """

    name = models.CharField(max_length=150, unique=True)
    code = models.CharField(
        max_length=50, unique=True,
        help_text="Short internal code e.g. 'XB', 'DL'",
    )
    is_active = models.BooleanField(default=True, db_index=True)
    supports_cod = models.BooleanField(default=True)
    logo_url = models.URLField(blank=True)
    tracking_url_template = models.CharField(
        max_length=500,
        blank=True,
        help_text="Use {awb} as placeholder. e.g. https://track.example.com/{awb}",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "courier"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class CourierServiceability(models.Model):
    """
    Stores which pincodes each courier can serve.
    A courier is serviceable for a route only if both origin
    and destination pincodes exist in this table for that courier.
    """

    courier = models.ForeignKey(
        Courier, on_delete=models.CASCADE, related_name="serviceability_records"
    )
    pin_code = models.CharField(max_length=6, db_index=True)
    is_pickup = models.BooleanField(
        default=False, help_text="Courier can pick up from this pincode"
    )
    is_delivery = models.BooleanField(
        default=True, help_text="Courier can deliver to this pincode"
    )

    class Meta:
        db_table = "courier_serviceability"
        unique_together = ("courier", "pin_code")
        indexes = [
            models.Index(fields=["pin_code", "courier"]),
        ]

    def __str__(self) -> str:
        modes = []
        if self.is_pickup:
            modes.append("pickup")
        if self.is_delivery:
            modes.append("delivery")
        return f"{self.courier.name} → {self.pin_code} ({', '.join(modes)})"