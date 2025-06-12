# SCOOTER_SHOP/inventory/models.py

from django.db import models
from django.urls import reverse
# Need to import the User model from the users app
from users.models import User


# Model for motorcycle conditions
class MotorcycleCondition(models.Model):
    name = models.CharField(max_length=20, unique=True)
    display_name = models.CharField(max_length=50)

    def __str__(self):
        return self.display_name
