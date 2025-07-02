                               

from django.db import models

class ServiceFAQ(models.Model):
    
    BOOKING_STEP_CHOICES = [
        ('service_page', 'Main Service Page'),
        ('step1', 'Step 1: Service Details'),
        ('step2', 'Step 2: Motorcycle Selection'),
        ('step3', 'Step 3: Your Motorcycle Details'),
        ('step4', 'Step 4: Your Profile'),
        ('step5', 'Step 5: Dropoff & Terms'),
        ('step6', 'Step 6: Payment'),
        ('step7', 'Step 7: Confirmation'),
        ('general', 'General Service Pages'),
    ]

    booking_step = models.CharField(
        max_length=20,
        choices=BOOKING_STEP_CHOICES,
        help_text="The step in the service booking process where this FAQ should be displayed."
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
        verbose_name = "Service FAQ"
        verbose_name_plural = "Service FAQs"
        ordering = ['booking_step', 'display_order', 'question']

    def __str__(self):
        return f"Q: {self.question} ({self.get_booking_step_display()})"
