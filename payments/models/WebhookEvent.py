from django.db import models
import uuid

class WebhookEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stripe_event_id = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="The unique ID of the Stripe webhook event (e.g., 'evt_...')."
    )
    event_type = models.CharField(
        max_length=100,
        help_text="The type of the Stripe event."
    )
    received_at = models.DateTimeField(
        auto_now_add=True,
        help_text="The timestamp when the webhook event was received and recorded."
    )
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
