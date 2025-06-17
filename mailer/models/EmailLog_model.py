from django.db import models
from django.conf import settings
from django.utils import timezone
from hire.models import HireBooking
from hire.models.driver_profile import DriverProfile
from service.models import ServiceBooking
from service.models import ServiceProfile
from inventory.models import SalesBooking # Import SalesBooking
from inventory.models import SalesProfile # Import SalesProfile


class EmailLog(models.Model):

    STATUS_CHOICES = (
        ('SENT', 'Sent'),
        ('FAILED', 'Failed'),
        ('PENDING', 'Pending'),
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

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_emails',
        help_text="The registered user associated with this email, if applicable."
    )

    driver_profile = models.ForeignKey(
        DriverProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_emails_for_driver',
        help_text="The driver profile associated with this email, if applicable."
    )

    service_profile = models.ForeignKey(
        ServiceProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_emails_for_service_profile',
        help_text="The service profile associated with this email, if applicable."
    )

    sales_profile = models.ForeignKey(
        SalesProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_emails_for_sales_profile',
        help_text="The sales profile associated with this email, if applicable."
    )

    booking = models.ForeignKey(
        HireBooking,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='related_emails_for_hire',
        help_text="The hire booking associated with this email, if applicable."
    )

    service_booking = models.ForeignKey(
        ServiceBooking,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='related_emails_for_service',
        help_text="The service booking associated with this email, if applicable."
    )

    sales_booking = models.ForeignKey(
        SalesBooking,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='related_emails_for_sales',
        help_text="The sales booking associated with this email, if applicable."
    )

    class Meta:
        verbose_name = "Email Log"
        verbose_name_plural = "Email Logs"
        ordering = ['-timestamp']

    def __str__(self):
        return f"Email to {self.recipient} - Subject: '{self.subject}' ({self.status})"
