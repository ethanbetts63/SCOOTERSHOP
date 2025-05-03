# service/forms.py

from django import forms
from django.utils.translation import gettext_lazy as _
import datetime # Needed for timedelta if used for duration

# Import models from the service app
from .models import ServiceType, CustomerMotorcycle, ServiceBooking
# Import models from other apps if needed
from inventory.models import Motorcycle # For transmission choices

# Service Booking Forms
class ServiceDetailsForm(forms.Form):
    # Queryset filtered in the view or in form init if needed based on availability
    service_type = forms.ModelChoiceField(
        queryset=ServiceType.objects.filter(is_active=True),
        empty_label="Select a Service Type",
        label="Service Type",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    appointment_datetime = forms.DateTimeField(
        label="Preferred Date and Time",
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'})
    )
    booking_comments = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        required=False,
        label="Comments or specific requests"
    )

    # Add a clean method for appointment_datetime if you need to validate against business hours or availability
    # def clean_appointment_datetime(self):
    #     appointment_dt = self.cleaned_data['appointment_datetime']
    #     # Add validation logic here (e.g., check if within business hours, in the future, etc.)
    #     return appointment_dt


class CustomerMotorcycleForm(forms.ModelForm):
    class Meta:
        model = CustomerMotorcycle
        fields = ['make', 'model', 'year', 'rego', 'vin_number', 'odometer', 'transmission']
        widgets = {
            # Using Motorcycle.TRANSMISSION_CHOICES assumes Motorcycle is accessible and has this attribute
            'transmission': forms.Select(choices=Motorcycle.TRANSMISSION_CHOICES, attrs={'class': 'form-control'}),
            'year': forms.NumberInput(attrs={'class': 'form-control', 'min': '1900', 'max': datetime.date.today().year}), # Example year validation
            'odometer': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'rego': forms.TextInput(attrs={'class': 'form-control'}),
            'vin_number': forms.TextInput(attrs={'class': 'form-control'}),
            'make': forms.TextInput(attrs={'class': 'form-control'}),
            'model': forms.TextInput(attrs={'class': 'form-control'}),
        }
        # Add labels or help text if needed
        # labels = {
        #     'rego': _('Registration Plate'),
        #     'vin_number': _('VIN Number'),
        # }

    def clean_rego(self):
         # Convert registration to uppercase if it exists
         if self.cleaned_data.get('rego'):
             return self.cleaned_data['rego'].upper()
         return self.cleaned_data.get('rego')

    def clean_vin_number(self):
         # Optional: Add VIN validation if needed
         return self.cleaned_data.get('vin_number')


class ServiceBookingUserForm(forms.Form):
    # These fields might overlap with User or custom user profile fields.
    # Consider using a ModelForm for a User profile if you collect more details.
    first_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    phone_number = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    preferred_contact = forms.ChoiceField(
        choices=ServiceBooking.CONTACT_CHOICES, # Assumes CONTACT_CHOICES is defined on the ServiceBooking model
        widget=forms.RadioSelect,
        initial='email',
        label="Preferred method of contact"
    )
    # The booking_comments field is now in ServiceDetailsForm for better grouping of booking-specific info

    # is_returning_customer field might be handled by checking if the user is authenticated
    # This field might not be necessary as a form field if the view logic handles it.
    # is_returning_customer = forms.BooleanField(label="Are you a returning customer?", required=False) # For anonymous users


class ExistingCustomerMotorcycleForm(forms.Form):
    # Queryset is set in the __init__ method based on the logged-in user
    motorcycle = forms.ModelChoiceField(
        queryset=CustomerMotorcycle.objects.none(),
        label="Select your Motorcycle",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        # Extract user from kwargs
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Set the queryset to show only motorcycles owned by this user
        if user and user.is_authenticated:
            # Assumes CustomerMotorcycle has a ForeignKey or OneToOneField to User named 'owner'
            self.fields['motorcycle'].queryset = CustomerMotorcycle.objects.filter(owner=user)
        else:
             # If user is anonymous, there are no existing motorcycles, so the queryset remains empty
             pass