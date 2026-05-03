from django.db import models


class Hub(models.Model):
    """
    A physical pickup hub operated by the company.
    When a user selects a hub instead of typing a pincode,
    we resolve the hub's pin_code and use that as the origin.
    """

    name = models.CharField(max_length=150)
    pin_code = models.CharField(max_length=6, db_index=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hub"
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} [{self.pin_code}]"
