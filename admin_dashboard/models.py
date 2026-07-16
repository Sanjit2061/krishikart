from django.db import models

class Offer(models.Model):
    title = models.CharField(max_length=200)
    code = models.CharField(max_length=30, unique=True)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    valid_from = models.DateField()
    valid_until = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} ({self.discount_percent}% off)"