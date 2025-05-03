# SCOOTER_SHOP/users/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models

# Custom User model extending Django's AbstractUser with additional fields
class User(AbstractUser):
    # Contact information fields
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address_line_1 = models.CharField(max_length=100, blank=True, null=True)
    address_line_2 = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=50, blank=True, null=True)
    state = models.CharField(max_length=50, blank=True, null=True)
    post_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=50, blank=True, null=True)

    # ID verification images
    id_image = models.FileField(upload_to='user_ids/', blank=True, null=True)
    international_id_image = models.FileField(upload_to='user_ids/international/', blank=True, null=True)

    # Add related_name to avoid reverse accessor clashes with Django's auth app
    # Ensure these are unique across your project if you have other apps
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions '
                  'granted to each of their groups.',
        related_name="users_user_set", # Changed related_name
        related_query_name="user",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name="users_user_permissions_set", # Changed related_name
        related_query_name="user",
    )

    def __str__(self):
        return f"{self.username} ({self.get_full_name() or self.email})"
