# mailer/models/mail_model.py

from django.db import models
from django.conf import settings # To access AUTH_USER_MODEL
from django.utils import timezone # To use timezone.now()
from hire.models import HireBooking
from hire.models.driver_profile import DriverProfile # Assuming driver_profile is in hire app
from service.models import ServiceBooking # NEW: Import ServiceBooking
from service.models import ServiceProfile # NEW: Import ServiceProfile


class EmailLog(models.Model):
    """
    Model to log all outgoing emails sent by the application.
    This provides a record of communication for auditing and debugging.
    The relationships to User, DriverProfile, HireBooking, ServiceBooking,
    and ServiceProfile are optional to allow for reuse across different
    application contexts.
    """

    # Choices for email status
    STATUS_CHOICES = (
        ('SENT', 'Sent'),
        ('FAILED', 'Failed'),
        ('PENDING', 'Pending'), # For emails that are queued but not yet sent
    )

    timestamp = models.DateTimeField(
        default=timezone.now,
        help_text="The date and time the email was attempted to be sent."
    )
    sender = models.CharField(
        max_length=255,
        help_text="The email address from which the email was sent."
    )
    recipient = models.CharField(
        max_length=255,
        help_text="The primary recipient's email address."
    )
    subject = models.CharField(
        max_length=255,
        help_text="The subject line of the email."
    )
    body = models.TextField(
        help_text="The full content (HTML or plain text) of the email body."
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='PENDING',
        help_text="The sending status of the email (e.g., Sent, Failed, Pending)."
    )
    error_message = models.TextField(
        blank=True,
        null=True,
        help_text="Any error message if the email sending failed."
    )

    # Optional Foreign key to the User model
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_emails',
        help_text="The registered user associated with this email, if applicable."
    )

    # Optional Foreign key to the DriverProfile model
    driver_profile = models.ForeignKey(
        DriverProfile, # Use the imported DriverProfile model
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_emails_for_driver', # Changed related_name to be specific
        help_text="The driver profile associated with this email, if applicable."
    )

    # NEW: Optional Foreign key to the ServiceProfile model
    service_profile = models.ForeignKey(
        ServiceProfile, # Use the imported ServiceProfile model
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_emails_for_service_profile', # Added explicit related_name
        help_text="The service profile associated with this email, if applicable."
    )

    # Optional Foreign key to the HireBooking model
    booking = models.ForeignKey(
        HireBooking,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='related_emails_for_hire', # Changed related_name to be explicit
        help_text="The hire booking associated with this email, if applicable."
    )

    # NEW: Optional Foreign key to the ServiceBooking model
    service_booking = models.ForeignKey(
        ServiceBooking,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='related_emails_for_service', # Added explicit related_name
        help_text="The service booking associated with this email, if applicable."
    )


    class Meta:
        verbose_name = "Email Log"
        verbose_name_plural = "Email Logs"
        ordering = ['-timestamp']

    def __str__(self):
        return f"Email to {self.recipient} - Subject: '{self.subject}' ({self.status})"

