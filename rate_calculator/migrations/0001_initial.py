import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Courier",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150, unique=True)),
                (
                    "code",
                    models.CharField(
                        help_text="Short internal code e.g. 'XB', 'DL'",
                        max_length=50,
                        unique=True,
                    ),
                ),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("supports_cod", models.BooleanField(default=True)),
                ("logo_url", models.URLField(blank=True)),
                (
                    "tracking_url_template",
                    models.CharField(
                        blank=True,
                        help_text="Use {awb} as placeholder. e.g. https://track.example.com/{awb}",
                        max_length=500,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "courier",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="Hub",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150)),
                ("pin_code", models.CharField(db_index=True, max_length=6)),
                ("city", models.CharField(max_length=100)),
                ("state", models.CharField(blank=True, max_length=100)),
                ("address", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "hub",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="ZoneMapping",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("origin_prefix", models.CharField(db_index=True, max_length=6)),
                ("destination_prefix", models.CharField(db_index=True, max_length=6)),
                (
                    "zone",
                    models.CharField(
                        choices=[
                            ("local", "Local"),
                            ("state", "Within State"),
                            ("metro", "Metro to Metro"),
                            ("roi", "Rest of India"),
                            ("special", "Special Zone"),
                        ],
                        max_length=20,
                    ),
                ),
            ],
            options={
                "db_table": "zone_mapping",
                "unique_together": {("origin_prefix", "destination_prefix")},
            },
        ),
        migrations.CreateModel(
            name="CourierServiceability",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("pin_code", models.CharField(db_index=True, max_length=6)),
                (
                    "is_pickup",
                    models.BooleanField(
                        default=False,
                        help_text="Courier can pick up from this pincode",
                    ),
                ),
                (
                    "is_delivery",
                    models.BooleanField(
                        default=True,
                        help_text="Courier can deliver to this pincode",
                    ),
                ),
                (
                    "courier",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="serviceability_records",
                        to="rate_calculator.courier",
                    ),
                ),
            ],
            options={
                "db_table": "courier_serviceability",
                "unique_together": {("courier", "pin_code")},
            },
        ),
        migrations.CreateModel(
            name="RateCard",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "zone",
                    models.CharField(
                        choices=[
                            ("local", "Local"),
                            ("state", "Within State"),
                            ("metro", "Metro to Metro"),
                            ("roi", "Rest of India"),
                            ("special", "Special Zone"),
                        ],
                        db_index=True,
                        max_length=20,
                    ),
                ),
                (
                    "service_type",
                    models.CharField(
                        choices=[("surface", "Surface"), ("air", "Air / Express")],
                        default="surface",
                        max_length=20,
                    ),
                ),
                (
                    "base_weight",
                    models.FloatField(
                        default=0.5,
                        help_text="Weight (kg) covered by the base charge",
                        validators=[django.core.validators.MinValueValidator(0.1)],
                    ),
                ),
                (
                    "base_charge",
                    models.FloatField(
                        help_text="Flat charge for shipments up to base_weight",
                        validators=[django.core.validators.MinValueValidator(0)],
                    ),
                ),
                (
                    "additional_weight_slab",
                    models.FloatField(
                        default=0.5,
                        help_text="Each extra slab size in kg",
                        validators=[django.core.validators.MinValueValidator(0.1)],
                    ),
                ),
                (
                    "additional_charge",
                    models.FloatField(
                        help_text="Charge per additional slab beyond base_weight",
                        validators=[django.core.validators.MinValueValidator(0)],
                    ),
                ),
                (
                    "rto_base_weight",
                    models.FloatField(
                        default=0.5,
                        validators=[django.core.validators.MinValueValidator(0.1)],
                    ),
                ),
                (
                    "rto_base_charge",
                    models.FloatField(
                        default=0,
                        validators=[django.core.validators.MinValueValidator(0)],
                    ),
                ),
                (
                    "rto_additional_weight_slab",
                    models.FloatField(
                        default=0.5,
                        validators=[django.core.validators.MinValueValidator(0.1)],
                    ),
                ),
                (
                    "rto_additional_charge",
                    models.FloatField(
                        default=0,
                        validators=[django.core.validators.MinValueValidator(0)],
                    ),
                ),
                (
                    "cod_fixed_charge",
                    models.FloatField(
                        default=0,
                        help_text="Minimum / flat COD charge",
                        validators=[django.core.validators.MinValueValidator(0)],
                    ),
                ),
                (
                    "cod_percent",
                    models.FloatField(
                        default=0,
                        help_text="Percentage of order_value; actual COD = max(fixed, percent-based)",
                        validators=[django.core.validators.MinValueValidator(0)],
                    ),
                ),
                (
                    "estimated_days",
                    models.PositiveIntegerField(
                        default=3,
                        help_text="Estimated transit days for this zone+service",
                    ),
                ),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "courier",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="rate_cards",
                        to="rate_calculator.courier",
                    ),
                ),
            ],
            options={
                "db_table": "rate_card",
                "unique_together": {("courier", "zone", "service_type")},
            },
        ),
        migrations.AddIndex(
            model_name="zonemapping",
            index=models.Index(
                fields=["origin_prefix", "destination_prefix", "zone"],
                name="zone_mappin_origin__9fa171_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="courierserviceability",
            index=models.Index(
                fields=["pin_code", "courier"],
                name="courier_ser_pin_cod_9a24a4_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="ratecard",
            index=models.Index(
                fields=["zone", "is_active"],
                name="rate_card_zone_7a2f42_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="ratecard",
            index=models.Index(
                fields=["courier", "zone", "service_type"],
                name="rate_card_courie_379d4d_idx",
            ),
        ),
    ]
