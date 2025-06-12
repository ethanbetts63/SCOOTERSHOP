# inventory/models/motorcycle_condition.py

from django.db import models

class MotorcycleCondition(models.Model):
    name = models.CharField(max_length=20, unique=True)
    display_name = models.CharField(max_length=50)

    def __str__(self):
        return self.display_name

