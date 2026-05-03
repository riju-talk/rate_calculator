from django.db import models


class Hub(models.Model):
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
