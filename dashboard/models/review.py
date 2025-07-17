from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Review(models.Model):
    """
    A review selected by an admin to be displayed on the website.
    This allows for manual creation or curation of reviews.
    """

    author_name = models.CharField(
        max_length=255, help_text="The name of the person who wrote the review."
    )
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5.",
    )
    text = models.TextField(help_text="The content of the review.")
    profile_photo_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Optional URL to the reviewer's profile picture.",
    )
    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Order in which the review is displayed. Lower numbers are shown first.",
    )
    is_active = models.BooleanField(
        default=True, help_text="Only active reviews will be displayed on the site."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "-created_at"]
        verbose_name = "Display Review"
        verbose_name_plural = "Display Reviews"

    def __str__(self):
        return f"Review by {self.author_name} - {self.rating} stars"
