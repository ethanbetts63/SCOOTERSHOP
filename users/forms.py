                             
                                                                             

from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User

                                     
class AdminUserCreationForm(UserCreationForm):
    class Meta:
        model = User
                                                                           
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
                                                                                    
                                                                                       
                                                                                                 
            "is_staff",
            "is_superuser",
            "is_active",
        )

                                                                   
class AdminUserChangeForm(UserChangeForm):
    class Meta:
        model = User
                                                                  
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