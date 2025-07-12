from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from dashboard.models import Notification
from .models import RefundTerms

@receiver(pre_save, sender=RefundTerms)
def capture_old_instance(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._old_instance = RefundTerms.objects.get(pk=instance.pk)
        except RefundTerms.DoesNotExist:
            instance._old_instance = None

@receiver(post_save, sender=RefundTerms)
def create_refund_terms_notification(sender, instance, created, **kwargs):
    if created:
        content_type = ContentType.objects.get_for_model(instance)
        Notification.objects.create(
            content_type=content_type,
            object_id=instance.pk,
            message=f"A new refund policy (v{instance.version_number}) has been created. Please review and update the content if necessary."
        )
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
            content_type = ContentType.objects.get_for_model(instance)
            Notification.objects.create(
                content_type=content_type,
                object_id=instance.pk,
                message=f"The refund settings for policy v{instance.version_number} have been updated. Please review the content to ensure it reflects these changes."
            )
