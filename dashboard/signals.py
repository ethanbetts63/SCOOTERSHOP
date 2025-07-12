from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType

from inventory.models import SalesBooking
from service.models import ServiceBooking
from core.models import Enquiry
from refunds.models import RefundRequest, RefundSettings

from .models import Notification

@receiver(post_save, sender=SalesBooking)
def create_sales_booking_notification(sender, instance, created, **kwargs):
    if created:
        message = f"New sales booking from {instance.sales_profile.name}"
        Notification.objects.create(content_object=instance, message=message)

@receiver(post_save, sender=ServiceBooking)
def create_service_booking_notification(sender, instance, created, **kwargs):
    if created:
        message = f"New service booking for {instance.service_profile.name}"
        Notification.objects.create(content_object=instance, message=message)

@receiver(post_save, sender=Enquiry)
def create_enquiry_notification(sender, instance, created, **kwargs):
    if created:
        message = f"New enquiry from {instance.name}"
        Notification.objects.create(content_object=instance, message=message)

@receiver(post_save, sender=RefundRequest)
def create_refund_notification(sender, instance, created, **kwargs):
    if created and instance.payment:
        customer_name = "Unknown Customer"
        if instance.payment.sales_customer_profile:
            customer_name = instance.payment.sales_customer_profile.name
        elif instance.payment.service_customer_profile:
            customer_name = instance.payment.service_customer_profile.name
        message = f"New refund request for {customer_name}"
        Notification.objects.create(content_object=instance, message=message)

@receiver(post_save, sender=RefundSettings)
def create_refund_settings_notification(sender, instance, created, **kwargs):
    if created:
        message = "Refund settings have been created. Please review the refund policy text."
        Notification.objects.create(content_object=instance, message=message)
    else:
        message = "Refund settings have been updated. Please review the refund policy text to ensure it reflects the changes."
        Notification.objects.create(content_object=instance, message=message)
