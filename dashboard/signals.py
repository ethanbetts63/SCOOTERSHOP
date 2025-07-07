from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType

from inventory.models import SalesBooking
from service.models import ServiceBooking
from core.models import Enquiry
from payments.models import RefundRequest

from .models import Notification

@receiver(post_save, sender=SalesBooking)
def create_sales_booking_notification(sender, instance, created, **kwargs):
    if created:
        message = f"New sales booking from {instance.sales_profile.name}"
        Notification.objects.create(content_object=instance, message=message)

@receiver(post_save, sender=ServiceBooking)
def create_service_booking_notification(sender, instance, created, **kwargs):
    if created:
        message = f"New service booking for {instance.customer_name}"
        Notification.objects.create(content_object=instance, message=message)

@receiver(post_save, sender=Enquiry)
def create_enquiry_notification(sender, instance, created, **kwargs):
    if created:
        message = f"New enquiry from {instance.name}"
        Notification.objects.create(content_object=instance, message=message)

@receiver(post_save, sender=RefundRequest)
def create_refund_notification(sender, instance, created, **kwargs):
    if created:
        message = f"New refund request for {instance.payment.customer}"
        Notification.objects.create(content_object=instance, message=message)
