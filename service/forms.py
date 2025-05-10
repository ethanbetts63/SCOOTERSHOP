# service/forms.py

from django import forms
from django.utils.translation import gettext_lazy as _
import datetime
from django.db.models import Q

from .models import ServiceType, CustomerMotorcycle, ServiceBooking
from inventory.models import Motorcycle
from users.models import User
# Import the BlockedDate model from the dashboard app
from dashboard.models import BlockedDate
# Import SiteSettings from dashboard for time slot generation
from dashboard.models import SiteSettings
from datetime import timedelta, time


# Abstract base form for common service booking fields
# Kept appointment_date and booking_comments here as they are used in Admin forms
class BaseAdminServiceBookingForm(forms.Form):
    service_type = forms.ModelChoiceField(
        queryset=ServiceType.objects.filter(is_active=True),
        empty_label="-- Select Service Type --",
        label="Service Type",
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )
    appointment_date = forms.DateTimeField(
        label="Preferred Date and Time",
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        required=True
    )
    booking_comments = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        required=False,
        label="Comments or specific requests"
    )


# --- Admin Booking Forms ---

# Form for creating a service booking for an anonymous/one-off customer
class AdminAnonBookingForm(BaseAdminServiceBookingForm):
    # One-off Customer Details
    one_off_first_name = forms.CharField(
        max_length=100,
        label="First Name",
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=True
    )
    one_off_last_name = forms.CharField(
        max_length=100,
        label="Last Name",
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=True
    )
    one_off_email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        required=False,
    )
    one_off_phone_number = forms.CharField(
        max_length=20,
        required=False,
        label="Phone Number",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    anon_customer_address = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        required=False,
        label="Address"
    )


    # Anonymous Vehicle Details
    anon_vehicle_make = forms.CharField(
        max_length=100,
        label="Make",
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=True
    )
    anon_vehicle_model = forms.CharField(
        max_length=100,
        label="Model",
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=True
    )
    anon_vehicle_year = forms.IntegerField(
        label="Year",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1900', 'max': datetime.date.today().year}),
        required=False,
    )
    anon_vehicle_rego = forms.CharField(
        max_length=20,
        required=False,
        label="Registration",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    anon_vehicle_vin_number = forms.CharField(
        max_length=50,
        required=False,
        label="VIN",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    anon_vehicle_odometer = forms.IntegerField(
        required=False,
        label="Odometer",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '0'})
    )
    anon_vehicle_transmission = forms.ChoiceField(
        choices=[('', '---------')] + list(Motorcycle.TRANSMISSION_CHOICES),
        required=False,
        label="Transmission",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    anon_engine_number = forms.CharField(
        max_length=50,
        required=False,
        label="Engine Number",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )


    # Clean method for the form
    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data



# Form for creating a service booking for an existing registered user
class AdminUserBookingForm(BaseAdminServiceBookingForm):
    user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).order_by('first_name', 'last_name'),
        empty_label="-- Select Existing Customer --",
        label="Existing Customer",
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )

    # Fields to optionally update user details (kept as required=False as per existing code)
    user_first_name = forms.CharField(
        max_length=100,
        required=False,
        label="Update First Name",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    user_last_name = forms.CharField(
        max_length=100,
        required=False,
        label="Update Last Name",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    user_email = forms.EmailField(
        required=False,
        label="Update Email",
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    user_phone_number = forms.CharField(
        max_length=20,
        required=False,
        label="Update Phone Number",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    # Choices for bike selection type
    BIKE_SELECTION_CHOICES = [
        ('existing', 'Select Existing Motorcycle'),
        ('new', 'Add New Motorcycle'),
    ]
    bike_selection_type = forms.ChoiceField(
        choices=BIKE_SELECTION_CHOICES,
        widget=forms.RadioSelect,
        initial='existing',
        label="Motorcycle Options",
        required=True
    )

    existing_motorcycle = forms.ModelChoiceField(
        queryset=CustomerMotorcycle.objects.none(),
        required=False,
        label="Existing Motorcycle",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    # Fields for adding a new motorcycle (Required is handled in clean method based on bike_selection_type)
    new_bike_make = forms.CharField(
        max_length=100,
        required=False,
        label="Make",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    new_bike_model = forms.CharField(
        max_length=100,
        required=False,
        label="Model",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    new_bike_year = forms.IntegerField(
        required=False,
        label="Year",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1900', 'max': datetime.date.today().year})
    )
    new_bike_rego = forms.CharField(
        max_length=20,
        required=False,
        label="Registration",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    new_bike_vin_number = forms.CharField(
        max_length=50,
        required=False,
        label="VIN Number",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    new_bike_odometer = forms.IntegerField(
        required=False,
        label="Odometer",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '0'})
    )
    new_bike_transmission = forms.ChoiceField(
        choices=[('', '---------')] + list(Motorcycle.TRANSMISSION_CHOICES),
        required=False,
        label="Transmission",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    # Initialize form to populate existing motorcycle queryset
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user_id = None
        if 'user' in self.data:
            try:
                user_id = int(self.data['user'])
            except (ValueError, TypeError):
                pass
        elif self.initial.get('user'):
             user_id = self.initial['user'].id if isinstance(self.initial['user'], User) else self.initial['user']

        if user_id:
            try:
                user = User.objects.get(id=user_id)
                self.fields['existing_motorcycle'].queryset = CustomerMotorcycle.objects.filter(owner=user).order_by('make', 'model')
            except User.DoesNotExist:
                pass

    # Clean method with conditional validation
    def clean(self):
        cleaned_data = super().clean()
        user = cleaned_data.get('user')
        bike_selection_type = cleaned_data.get('bike_selection_type')
        existing_motorcycle = cleaned_data.get('existing_motorcycle')
        new_bike_make = cleaned_data.get('new_bike_make')
        new_bike_model = cleaned_data.get('new_bike_model')
        new_bike_year = cleaned_data.get('new_bike_year')

        # The 'user' field is now required at the field level, but we keep this check
        # for clarity and consistency with existing logic.
        if not user:
            self.add_error('user', 'Please select an existing customer.')

        # Validate bike selection based on type
        if bike_selection_type == 'existing':
            if not existing_motorcycle:
                self.add_error('existing_motorcycle', 'Please select an existing motorcycle.')
            # Ensure new bike fields are empty - this validation remains
            if new_bike_make or new_bike_model or new_bike_year is not None:
                 self.add_error(None, 'New bike details should not be provided when selecting an existing bike.')

        elif bike_selection_type == 'new':
            # These fields are now explicitly required by the user's request
            if not new_bike_make:
                self.add_error('new_bike_make', 'Make is required for a new motorcycle.')
            if not new_bike_model:
                self.add_error('new_bike_model', 'Model is required for a new motorcycle.')
            if not new_bike_year:
                self.add_error('new_bike_year', 'Year is required for a new motorcycle.')
            # Ensure existing motorcycle field is empty - this validation remains
            if existing_motorcycle:
                 self.add_error('existing_motorcycle', 'Cannot select an existing motorcycle when adding a new one.')

        return cleaned_data

# Form for basic service details (frontend customer form - Step 1)
class ServiceDetailsForm(forms.Form):
    service_type = forms.ModelChoiceField(
        queryset=ServiceType.objects.filter(is_active=True),
        empty_label="Select a Service Type",
        label="Service Type",
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )
    # Changed from DateTimeField to DateField
    appointment_date = forms.DateField(
        label="Preferred Date",
        # We will use Flatpickr for the date input in the template
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'text'}), # Use type text for Flatpickr
        required=True
    )
    # Added a ChoiceField for drop-off time
    drop_off_time = forms.ChoiceField(
        label="Preferred Drop-off Time",
        choices=[], # Choices will be populated dynamically in the view
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )

    # Add a clean method to validate that a time slot was selected
    def clean(self):
        cleaned_data = super().clean()
        # Check if a drop_off_time was provided.
        # The choices are populated in the view, so we just check if a value was selected.
        drop_off_time = cleaned_data.get('drop_off_time')
        if not drop_off_time:
             self.add_error('drop_off_time', 'Please select a valid drop-off time.')

        # Add any other necessary cross-field validation here
        return cleaned_data

# Model form for customer motorcycles (no changes requested)
class CustomerMotorcycleForm(forms.ModelForm):
    class Meta:
        model = CustomerMotorcycle
        fields = ['make', 'model', 'year', 'rego', 'odometer', 'vin_number', 'transmission']
        widgets = {
            'transmission': forms.Select(choices=Motorcycle.TRANSMISSION_CHOICES, attrs={'class': 'form-control'}),
            'year': forms.NumberInput(attrs={'class': 'form-control', 'min': '1900', 'max': datetime.date.today().year}),
            'odometer': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'rego': forms.TextInput(attrs={'class': 'form-control'}),
            'vin_number': forms.TextInput(attrs={'class': 'form-control'}),
            'make': forms.TextInput(attrs={'class': 'form-control'}),
            'model': forms.TextInput(attrs={'class': 'form-control'}),
        }

    # Clean the rego field
    def clean_rego(self):
         if self.cleaned_data.get('rego'):
             return self.cleaned_data['rego'].upper()
         return self.cleaned_data.get('rego')

    # Clean the vin_number field
    def clean_vin_number(self):
         return self.cleaned_data.get('vin_number')


# Form for service booking by an existing user (Step 3)
class ServiceBookingUserForm(forms.Form):
    first_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=True
    )
    last_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=True
    )
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}), required=True)
    phone_number = forms.CharField(max_length=20, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    preferred_contact = forms.ChoiceField(
        choices=ServiceBooking.CONTACT_CHOICES,
        widget=forms.RadioSelect,
        initial='email',
        label="Preferred method of contact",
        required=True
    )
    booking_comments = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        required=False,
        label="Comments or specific requests"
    )

# Form to select an existing customer motorcycle (no changes requested on required fields)
class ExistingCustomerMotorcycleForm(forms.Form):
    motorcycle = forms.ModelChoiceField(
        queryset=CustomerMotorcycle.objects.none(),
        label="Select your Motorcycle",
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )

    # Initialize form with user's motorcycles
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and user.is_authenticated:
            self.fields['motorcycle'].queryset = CustomerMotorcycle.objects.filter(owner=user)