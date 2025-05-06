# service/forms.py

from django import forms
from django.utils.translation import gettext_lazy as _
import datetime
from django.db.models import Q # Import Q for potential lookups later

# Import models from the service app
from .models import ServiceType, CustomerMotorcycle, ServiceBooking
# Import models from other apps if needed
from inventory.models import Motorcycle # For transmission choices
from users.models import User # Import the User model

# Service Booking Forms (Keep existing forms for other flows)
class ServiceDetailsForm(forms.Form):
    # ... (existing code) ...
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

class CustomerMotorcycleForm(forms.ModelForm):
    class Meta:
        model = CustomerMotorcycle
        fields = ['make', 'model', 'year', 'rego', 'vin_number', 'odometer', 'transmission']
        widgets = {
            'transmission': forms.Select(choices=Motorcycle.TRANSMISSION_CHOICES, attrs={'class': 'form-control'}),
            'year': forms.NumberInput(attrs={'class': 'form-control', 'min': '1900', 'max': datetime.date.today().year}),
            'odometer': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'rego': forms.TextInput(attrs={'class': 'form-control'}),
            'vin_number': forms.TextInput(attrs={'class': 'form-control'}),
            'make': forms.TextInput(attrs={'class': 'form-control'}),
            'model': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_rego(self):
         if self.cleaned_data.get('rego'):
             return self.cleaned_data['rego'].upper()
         return self.cleaned_data.get('rego')

    def clean_vin_number(self):
         return self.cleaned_data.get('vin_number')

class ServiceBookingUserForm(forms.Form):
    # ... (existing code) ...
    first_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    phone_number = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    preferred_contact = forms.ChoiceField(
        choices=ServiceBooking.CONTACT_CHOICES,
        widget=forms.RadioSelect,
        initial='email',
        label="Preferred method of contact"
    )
    booking_comments = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        required=False,
        label="Comments or specific requests"
    )

class ExistingCustomerMotorcycleForm(forms.Form):
    # ... (existing code) ...
    motorcycle = forms.ModelChoiceField(
        queryset=CustomerMotorcycle.objects.none(),
        label="Select your Motorcycle",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and user.is_authenticated:
            self.fields['motorcycle'].queryset = CustomerMotorcycle.objects.filter(owner=user)
        else:
             pass # Queryset remains empty for anonymous users


# --- Admin Booking Form ---
class AdminBookingForm(forms.Form):
    CUSTOMER_TYPE_CHOICES = [
        ('existing', 'Existing Customer'),
        ('one_off', 'One-off / Anonymous'),
    ]
    customer_type = forms.ChoiceField(
        choices=CUSTOMER_TYPE_CHOICES,
        widget=forms.RadioSelect,
        initial='existing',
        label="Customer Type"
    )

    user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True), # Only active users
        empty_label="-- Select Existing Customer --",
        label="Existing Customer",
        required=False, # Not required initially, depends on customer_type
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    # Fields for One-off / Anonymous Customer Details
    one_off_first_name = forms.CharField(
        max_length=100,
        required=False, # Required based on customer_type
        label="First Name",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    one_off_last_name = forms.CharField(
        max_length=100,
        required=False, # Required based on customer_type
        label="Last Name",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    one_off_email = forms.EmailField(
        required=False, # Required based on customer_type
        label="Email",
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    one_off_phone_number = forms.CharField(
        max_length=20,
        required=False, # Optional for one-off
        label="Phone Number",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    # Fields for Motorcycle Details (for both existing and one-off)
    BIKE_SELECTION_CHOICES = [
        ('existing', 'Select Existing Motorcycle'),
        ('new', 'Add New Motorcycle'),
    ]
    bike_selection_type = forms.ChoiceField(
        choices=BIKE_SELECTION_CHOICES,
        widget=forms.RadioSelect,
        initial='existing',
        label="Motorcycle Options"
    )

    existing_motorcycle = forms.ModelChoiceField(
        queryset=CustomerMotorcycle.objects.none(), # Will be populated dynamically
        required=False, # Make required based on bike_selection_type and customer_type
        label="Existing Motorcycle",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    # Fields for adding a new motorcycle (mimicking CustomerMotorcycleForm)
    new_bike_make = forms.CharField(
        max_length=100,
        required=False, # Make required based on bike_selection_type and customer_type
        label="Make",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    new_bike_model = forms.CharField(
        max_length=100,
        required=False, # Make required based on bike_selection_type and customer_type
        label="Model",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    new_bike_year = forms.IntegerField(
        required=False, # Make required based on bike_selection_type and customer_type
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
        choices=[('', '---------')] + list(Motorcycle.TRANSMISSION_CHOICES), # Add an empty choice
        required=False,
        label="Transmission",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    # Service Details fields
    service_type = forms.ModelChoiceField(
        queryset=ServiceType.objects.filter(is_active=True),
        empty_label="-- Select Service Type --",
        label="Service Type",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    appointment_datetime = forms.DateTimeField(
        label="Preferred Date and Time",
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'})
    )

    # Customer Contact/Comments fields
    preferred_contact = forms.ChoiceField(
        choices=ServiceBooking.CONTACT_CHOICES,
        widget=forms.RadioSelect,
        initial='email',
        label="Preferred method of contact"
    )
    booking_comments = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        required=False,
        label="Comments or specific requests"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initially, the existing_motorcycle queryset is empty.
        # It will be populated dynamically via JavaScript/AJAX based on the selected user.
        # Or, if data is posted, we can populate it based on the posted user.

        # If there's data in the form (e.g., POST request or initial data),
        # try to populate the existing_motorcycle queryset based on the user.
        user_id = None
        # Check POST data first
        if 'user' in self.data:
            try:
                user_id = int(self.data['user'])
            except (ValueError, TypeError):
                pass
        # If not in POST data, check initial data
        elif self.initial.get('user'):
             user_id = self.initial['user'].id if isinstance(self.initial['user'], User) else self.initial['user']


        if user_id:
            try:
                user = User.objects.get(id=user_id)
                self.fields['existing_motorcycle'].queryset = CustomerMotorcycle.objects.filter(owner=user)
            except User.DoesNotExist:
                # User not found, queryset remains empty
                pass

    def clean(self):
        cleaned_data = super().clean()
        customer_type = cleaned_data.get('customer_type')
        user = cleaned_data.get('user')
        one_off_first_name = cleaned_data.get('one_off_first_name')
        one_off_last_name = cleaned_data.get('one_off_last_name')
        one_off_email = cleaned_data.get('one_off_email')

        bike_selection_type = cleaned_data.get('bike_selection_type')
        existing_motorcycle = cleaned_data.get('existing_motorcycle')
        new_bike_make = cleaned_data.get('new_bike_make')
        new_bike_model = cleaned_data.get('new_bike_model')
        new_bike_year = cleaned_data.get('new_bike_year')
        anon_vehicle_make = cleaned_data.get('anon_vehicle_make')
        anon_vehicle_model = cleaned_data.get('anon_vehicle_model')
        anon_vehicle_year = cleaned_data.get('anon_vehicle_year')


        if customer_type == 'existing':
            if not user:
                self.add_error('user', 'Please select an existing customer.')
            # Ensure one-off fields are empty
            if one_off_first_name or one_off_last_name or one_off_email:
                 self.add_error(None, 'One-off customer details should not be provided when selecting an existing customer.')
            # Ensure anonymous vehicle fields are empty
            if anon_vehicle_make or anon_vehicle_model or anon_vehicle_year is not None:
                 self.add_error(None, 'Anonymous vehicle details should not be provided for an existing customer.')

            # Validate bike selection for existing customer
            if bike_selection_type == 'existing':
                if not existing_motorcycle:
                    self.add_error('existing_motorcycle', 'Please select an existing motorcycle.')
                if new_bike_make or new_bike_model or new_bike_year is not None:
                    self.add_error(None, 'New bike details should not be provided when selecting an existing bike.')
            elif bike_selection_type == 'new':
                if not new_bike_make:
                    self.add_error('new_bike_make', 'Make is required for a new motorcycle.')
                if not new_bike_model:
                    self.add_error('new_bike_model', 'Model is required for a new motorcycle.')
                if not new_bike_year:
                    self.add_error('new_bike_year', 'Year is required for a new motorcycle.')
                if existing_motorcycle:
                    self.add_error('existing_motorcycle', 'Cannot select an existing motorcycle when adding a new one.')

        elif customer_type == 'one_off':
            # Ensure user field is empty
            if user:
                 self.add_error('user', 'Cannot select an existing customer for a one-off booking.')
            # Ensure one-off fields are provided
            if not one_off_first_name:
                self.add_error('one_off_first_name', 'First Name is required for a one-off booking.')
            if not one_off_last_name:
                self.add_error('one_off_last_name', 'Last Name is required for a one-off booking.')
            if not one_off_email:
                self.add_error('one_off_email', 'Email is required for a one-off booking.')
            # Email format is validated by forms.EmailField

            # Validate anonymous vehicle details
            # Assuming either existing motorcycle is selected (unlikely for one-off, but handled by logic below)
            # or new vehicle details are provided via the anon_vehicle_* fields
            # We'll make anon_vehicle_make, model, and year required for one-off bookings.
            if not anon_vehicle_make:
                 self.add_error('anon_vehicle_make', 'Vehicle Make is required for a one-off booking.')
            if not anon_vehicle_model:
                 self.add_error('anon_vehicle_model', 'Vehicle Model is required for a one-off booking.')
            if not anon_vehicle_year:
                 self.add_error('anon_vehicle_year', 'Vehicle Year is required for a one-off booking.')
            # Ensure existing/new motorcycle fields for registered users are empty
            if existing_motorcycle or new_bike_make or new_bike_model or new_bike_year is not None:
                 self.add_error(None, 'Existing or new motorcycle details (for registered users) should not be provided for a one-off booking.')


        return cleaned_data