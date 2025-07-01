                                            

from django.db import models

class SalesFAQ(models.Model):
    """
    Model to store Frequently Asked Questions for the sales/booking process.
    """
    BOOKING_STEP_CHOICES = [
        ('step1', 'Step 1: Your Details'),
        ('step2', 'Step 2: Booking Details & Appointment'),
        ('step3', 'Step 3: Payment'),
        ('step4', 'Step 4: Confirmation'),
        ('general', 'General Sales Pages'),
    ]

    booking_step = models.CharField(
        max_length=20,
        choices=BOOKING_STEP_CHOICES,
        help_text="The step in the booking process where this FAQ should be displayed."
    )
    question = models.CharField(
        max_length=255,
        help_text="The frequently asked question."
    )
    answer = models.TextField(
        help_text="The answer to the question."
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Designates whether this FAQ is publicly visible."
    )
    display_order = models.PositiveIntegerField(
        default=0,
        help_text="The order in which the FAQ appears. Lower numbers are displayed first."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Sales FAQ"
        verbose_name_plural = "Sales FAQs"
        ordering = ['booking_step', 'display_order', 'question']

    def __str__(self):
        return f"Q: {self.question} ({self.get_booking_step_display()})"
