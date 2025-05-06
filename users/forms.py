# SCOOTER_SHOP/users/forms.py
# You'll need to create a new file named forms.py in your users app directory

from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User

# Form for admin to create a new user
class AdminUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        # Include all fields you want the admin to be able to set initially
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "address_line_1",
            "address_line_2",
            "city",
            "state",
            "post_code",
            "country",
            # You might not want to include id_image or international_id_image here,
            # as file uploads often require separate handling or a different form flow.
            # Add 'is_staff', 'is_superuser', 'is_active' if you want admin to set these directly
            "is_staff",
            "is_superuser",
            "is_active",
        )

# You might also want a form for admin to edit existing users later
class AdminUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        # Include all fields you want the admin to be able to edit
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "address_line_1",
            "address_line_2",
            "city",
            "state",
            "post_code",
            "country",
            "id_image",
            "international_id_image",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
            "user_permissions",
        )