# users/admin.py

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin # Import default UserAdmin

# Assuming your User model is accessible via get_user_model()
User = get_user_model()

# If you need to unregister the default User admin provided by Django auth
# This is often done when you have a custom User model or custom admin options
# try:
#     admin.site.unregister(User)
# except admin.sites.NotRegistered:
#     pass # Handle case where User was never registered initially

# Register your User model with the admin site
# Use the default UserAdmin or a custom one if you uncommented the block above
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # Customize the admin options for your User model here if needed
    # Example: Add custom fields to list_display, fieldsets, etc.
    # list_display = UserAdmin.list_display + ('some_custom_field',)
    pass

# If you have any other user-related models (e.g., UserProfile)
# from .models import UserProfile
# @admin.register(UserProfile)
# class UserProfileAdmin(admin.ModelAdmin):
#     list_display = ('user', 'some_field')
#     search_fields = ('user__username',)