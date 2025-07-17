from django.db import models
from .motorcycle import Motorcycle


class FeaturedMotorcycle(models.Model):
    CATEGORY_CHOICES = [
        ("new", "New"),
        ("used", "Used"),
    ]

    motorcycle = models.ForeignKey(
        Motorcycle, on_delete=models.CASCADE, related_name="featured_entries"
    )
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)
    order = models.PositiveIntegerField(
        default=0,
        help_text="Order in which the motorcycle appears. Lower numbers appear first.",
    )

    class Meta:
        ordering = ["order"]
        verbose_name = "Featured Motorcycle"
        verbose_name_plural = "Featured Motorcycles"

    def __str__(self):
        return f"{self.motorcycle.title} (Featured {self.get_category_display()})"
