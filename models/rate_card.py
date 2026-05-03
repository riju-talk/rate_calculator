from django.db import models
from django.core.validators import MinValueValidator
from .courier import Courier


class RateCard(models.Model):
    """
    Pricing configuration for a courier on a specific zone + service type.

    Charge components
    -----------------
    Forward:
        base_charge          — flat charge for shipments up to base_weight
        additional_charge    — per additional_weight_slab beyond base_weight

    RTO (Return To Origin):
        rto_base_charge      — flat charge for RTO up to rto_base_weight
        rto_additional_charge — per rto_additional_weight_slab beyond rto_base_weight

    COD:
        cod_fixed_charge     — minimum/flat COD handling fee
        cod_percent          — percentage of order_value (whichever is higher wins)

    GST is applied on top of the sub-total (rate pulled from Django settings).
    """

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

    courier = models.ForeignKey(Courier, on_delete=models.CASCADE, related_name="rate_cards")
    zone = models.CharField(max_length=20, choices=ZONE_CHOICES, db_index=True)
    service_type = models.CharField(max_length=20, choices=SERVICE_CHOICES, default="surface")

    # ── Forward charges ──────────────────────────────────────────────────────
    base_weight = models.FloatField(
        default=0.5, validators=[MinValueValidator(0.1)],
        help_text="Weight (kg) covered by the base charge",
    )
    base_charge = models.FloatField(
        validators=[MinValueValidator(0)],
        help_text="Flat charge for shipments up to base_weight",
    )
    additional_weight_slab = models.FloatField(
        default=0.5, validators=[MinValueValidator(0.1)],
        help_text="Each extra slab size in kg",
    )
    additional_charge = models.FloatField(
        validators=[MinValueValidator(0)],
        help_text="Charge per additional slab beyond base_weight",
    )

    # ── RTO charges ──────────────────────────────────────────────────────────
    rto_base_weight = models.FloatField(default=0.5, validators=[MinValueValidator(0.1)])
    rto_base_charge = models.FloatField(default=0, validators=[MinValueValidator(0)])
    rto_additional_weight_slab = models.FloatField(default=0.5, validators=[MinValueValidator(0.1)])
    rto_additional_charge = models.FloatField(default=0, validators=[MinValueValidator(0)])

    # ── COD charges ──────────────────────────────────────────────────────────
    cod_fixed_charge = models.FloatField(
        default=0, validators=[MinValueValidator(0)],
        help_text="Minimum / flat COD charge",
    )
    cod_percent = models.FloatField(
        default=0, validators=[MinValueValidator(0)],
        help_text="Percentage of order_value; actual COD = max(fixed, percent-based)",
    )

    # ── Meta ─────────────────────────────────────────────────────────────────
    estimated_days = models.PositiveIntegerField(
        default=3, help_text="Estimated transit days for this zone+service"
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