from django.core.validators import MinValueValidator
from django.db import models


class RateCard(models.Model):
    ZONE_CHOICES = [
        ("local", "Local"),
        ("state", "Within State"),
        ("metro", "Metro to Metro"),
        ("roi", "Rest of India"),
        ("special", "Special Zone"),
    ]

    SERVICE_CHOICES = [
        ("surface", "Surface"),
        ("air", "Air / Express"),
    ]

    courier = models.ForeignKey(
        "Courier",
        on_delete=models.CASCADE,
        related_name="rate_cards",
    )
    zone = models.CharField(max_length=20, choices=ZONE_CHOICES, db_index=True)
    service_type = models.CharField(
        max_length=20,
        choices=SERVICE_CHOICES,
        default="surface",
    )

    base_weight = models.FloatField(
        default=0.5,
        validators=[MinValueValidator(0.1)],
        help_text="Weight (kg) covered by the base charge",
    )
    base_charge = models.FloatField(
        validators=[MinValueValidator(0)],
        help_text="Flat charge for shipments up to base_weight",
    )
    additional_weight_slab = models.FloatField(
        default=0.5,
        validators=[MinValueValidator(0.1)],
        help_text="Each extra slab size in kg",
    )
    additional_charge = models.FloatField(
        validators=[MinValueValidator(0)],
        help_text="Charge per additional slab beyond base_weight",
    )

    rto_base_weight = models.FloatField(
        default=0.5,
        validators=[MinValueValidator(0.1)],
    )
    rto_base_charge = models.FloatField(
        default=0,
        validators=[MinValueValidator(0)],
    )
    rto_additional_weight_slab = models.FloatField(
        default=0.5,
        validators=[MinValueValidator(0.1)],
    )
    rto_additional_charge = models.FloatField(
        default=0,
        validators=[MinValueValidator(0)],
    )

    cod_fixed_charge = models.FloatField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Minimum / flat COD charge",
    )
    cod_percent = models.FloatField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Percentage of order_value; actual COD = max(fixed, percent-based)",
    )

    estimated_days = models.PositiveIntegerField(
        default=3,
        help_text="Estimated transit days for this zone+service",
    )
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rate_card"
        unique_together = ("courier", "zone", "service_type")
        indexes = [
            models.Index(fields=["zone", "is_active"]),
            models.Index(fields=["courier", "zone", "service_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.courier.name} | {self.zone} | {self.service_type}"
