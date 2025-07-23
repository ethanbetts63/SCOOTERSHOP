from django.db import models

class Color(models.Model):
    name = models.CharField(max_length=50, unique=True)
    hex_code = models.CharField(max_length=7, blank=True, help_text="Optional: e.g., #FF5733")

    def __str__(self):
        return self.name
