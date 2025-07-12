from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType

from inventory.models import SalesBooking
from service.models import ServiceBooking
from core.models import Enquiry
from refunds.models import RefundRequest, RefundTerms

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

@receiver(pre_save, sender=RefundTerms)
def capture_old_refund_terms_instance(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._old_instance = RefundTerms.objects.get(pk=instance.pk)
        except RefundTerms.DoesNotExist:
            instance._old_instance = None

@receiver(post_save, sender=RefundTerms)
def create_refund_terms_notification(sender, instance, created, **kwargs):
    if created:
        message = f"A new refund policy (v{instance.version_number}) has been created. Please review and update the content if necessary."
        Notification.objects.create(content_object=instance, message=message)
    elif hasattr(instance, '_old_instance') and instance._old_instance is not None:
        old = instance._old_instance
        if any([
            old.deposit_full_refund_days != instance.deposit_full_refund_days,
            old.deposit_partial_refund_days != instance.deposit_partial_refund_days,
            old.deposit_partial_refund_percentage != instance.deposit_partial_refund_percentage,
            old.deposit_no_refund_days != instance.deposit_no_refund_days,
            old.full_payment_full_refund_days != instance.full_payment_full_refund_days,
            old.full_payment_partial_refund_days != instance.full_payment_partial_refund_days,
            old.full_payment_partial_refund_percentage != instance.full_payment_partial_refund_percentage,
            old.full_payment_no_refund_days != instance.full_payment_no_refund_days
        ]):
            message = f"The refund settings for policy v{instance.version_number} have been updated. Please review the content to ensure it reflects these changes."
            Notification.objects.create(content_object=instance, message=message)
