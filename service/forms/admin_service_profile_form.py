from django import forms
from service.models import ServiceProfile
from django.contrib.auth import get_user_model # Import get_user_model to dynamically get the User model

# Get the User model
User = get_user_model()

class AdminServiceProfileForm(forms.ModelForm):
    """
    Form for administrators to create and manage ServiceProfile instances.
    Includes an optional field to link an existing Django User account.
    """
    user = forms.ModelChoiceField(
        queryset=User.objects.all().order_by('username'), # Query all User instances, ordered by username
        required=False, # Make this field optional
        empty_label="-- No User Account --", # Option to select no user
        help_text="Optionally link this Service Profile to an existing user account.",
        widget=forms.Select(attrs={'class': 'form-control'}) # Apply basic Bootstrap styling
    )

    class Meta:
        model = ServiceProfile
        fields = [
            'user', # Add the user field here
            'name',
            'email',
            'phone_number',
            'address_line_1',
            'address_line_2',
            'city',
            'state',
            'post_code',
            'country',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'address_line_1': forms.TextInput(attrs={'class': 'form-control'}),
            'address_line_2': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'post_code': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'user': 'Linked User Account',
            'name': 'Full Name',
            'email': 'Email Address',
            'phone_number': 'Phone Number',
            'address_line_1': 'Address Line 1',
            'address_line_2': 'Address Line 2 (Optional)',
            'city': 'City',
            'state': 'State/Province',
            'post_code': 'Post Code',
            'country': 'Country',
        }

    def clean_user(self):
        """
        Custom clean method for the 'user' field to ensure that if a user is
        selected, they don't already have a service profile linked.
        """
        user = self.cleaned_data.get('user')
        # If we are updating an existing instance and the user hasn't changed,
        # or no user is selected, skip this validation.
        if user and user != self.instance.user:
            # Check if this user already has a service profile
            if ServiceProfile.objects.filter(user=user).exists():
                # If an instance is being updated and the user is the same,
                # or if the current instance is the one being edited,
                # then it's valid. This prevents false positives when editing
                # an existing profile.
                if self.instance and self.instance.user == user:
                    pass
                else:
                    raise forms.ValidationError(
                        f"This user ({user.username}) is already linked to another Service Profile."
                    )
        return user

    def clean(self):
        """
        Custom validation to ensure either 'user' is provided OR 'name', 'email', and 'phone_number' are provided.
        Also, prevents linking a user that already has a profile, unless it's the current profile being edited.
        """
        cleaned_data = super().clean()
        user = cleaned_data.get('user')
        name = cleaned_data.get('name')
        email = cleaned_data.get('email')
        phone_number = cleaned_data.get('phone_number')

        # If no user is selected, then name, email, and phone_number become mandatory.
        if not user:
            if not name:
                self.add_error('name', "Full Name is required if no user account is linked.")
            if not email:
                self.add_error('email', "Email Address is required if no user account is linked.")
            if not phone_number:
                self.add_error('phone_number', "Phone Number is required if no user account is linked.")

        return cleaned_data
