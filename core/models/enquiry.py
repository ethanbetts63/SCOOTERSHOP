from django.db import models
from django.urls import reverse
from inventory.models import Motorcycle


class Enquiry(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    message = models.TextField()
    motorcycle = models.ForeignKey(Motorcycle, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Enquiries"

    def __str__(self):
        return f"Enquiry from {self.name} ({self.email})"

    def get_absolute_url(self):
        return reverse('core:admin_enquiry_details', args=[str(self.id)])
