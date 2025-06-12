# Model for storing additional motorcycle images
from django.db import models

class MotorcycleImage(models.Model):
    motorcycle = models.ForeignKey(Motorcycle, on_delete=models.CASCADE, related_name='images')
    image = models.FileField(upload_to='motorcycles/additional/')

    def __str__(self):
        return f"Image for {self.motorcycle}"
