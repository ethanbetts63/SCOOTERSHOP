# payments/models/WebhookEvent.py
from django.db import models
import uuid

class WebhookEvent(models.Model):
    """
    Records processed Stripe webhook events to ensure idempotency.
    If an event ID already exists, it means the event has been processed.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # The unique ID provided by Stripe for each webhook event.
    # This is crucial for idempotency.
    stripe_event_id = models.CharField(
        max_length=100,
        unique=True,
        db_index=True, # Add index for faster lookups
        help_text="The unique ID of the Stripe webhook event (e.g., 'evt_...')."
    )
    # The type of the Stripe event (e.g., 'payment_intent.succeeded').
    event_type = models.CharField(
        max_length=100,
        help_text="The type of the Stripe event."
    )
    # Timestamp when the event was received and recorded.
    received_at = models.DateTimeField(
        auto_now_add=True,
        help_text="The timestamp when the webhook event was received and recorded."
    )
    # Optional: Store the full event payload for debugging/auditing
    payload = models.JSONField(
        blank=True,
        null=True,
        help_text="The full JSON payload of the Stripe webhook event."
    )

    class Meta:
        verbose_name = "Stripe Webhook Event"
        verbose_name_plural = "Stripe Webhook Events"
        ordering = ['-received_at']

    def __str__(self):
        return f"Event: {self.stripe_event_id} ({self.event_type}) received at {self.received_at}"

