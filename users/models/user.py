from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    def __str__(self):
        return f"{self.username} ({self.get_full_name() or self.email})"
