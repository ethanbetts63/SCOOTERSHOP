# users/admin.py

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin # Import default UserAdmin

# Assuming your User model is accessible via get_user_model()
User = get_user_model()

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    pass
