from django.db import models


class ZoneMapping(models.Model):
    """
    Maps pairs of pincode prefixes to a shipping zone.

    Zone hierarchy (evaluated top-to-bottom):
        special  → North East states, J&K, Andaman etc.
        local    → same city / same pincode prefix
        metro    → metro-to-metro routes
        state    → within the same state
        roi      → rest of India (default fallback)

    Populate this table via a data migration or management command.
    Prefix length is flexible: use 3 digits for district-level or
    2 digits for state-level mappings.
    """

    ZONE_CHOICES = [
        ("local", "Local"),
        ("state", "Within State"),
        ("metro", "Metro to Metro"),
        ("roi", "Rest of India"),
        ("special", "Special Zone"),
    ]

    origin_prefix = models.CharField(max_length=6, db_index=True)
    destination_prefix = models.CharField(max_length=6, db_index=True)
    zone = models.CharField(max_length=20, choices=ZONE_CHOICES)

    class Meta:
        db_table = "zone_mapping"
        unique_together = ("origin_prefix", "destination_prefix")
        indexes = [
            models.Index(fields=["origin_prefix", "destination_prefix", "zone"]),
        ]

    def __str__(self) -> str:
        return f"{self.origin_prefix} → {self.destination_prefix} : {self.zone}"