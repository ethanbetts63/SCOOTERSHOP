
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

class Notification(models.Model):
    """
    A notification for an admin-facing event.
    """
    CONTENT_TYPE_CHOICES = (
        models.Q(app_label='inventory', model='salesbooking') |
        models.Q(app_label='service', model='servicebooking') |
        models.Q(app_label='core', model='enquiry') |
        models.Q(app_label='refunds', model='refundrequest') |
        models.Q(app_label='refunds', model='refundterms')
    )

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to=CONTENT_TYPE_CHOICES
    )
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    message = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    is_cleared = models.BooleanField(default=False)

    def __str__(self):
        return self.message

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
