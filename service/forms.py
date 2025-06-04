# # service/forms.py

# from django import forms
# from django.utils.translation import gettext_lazy as _
# import datetime
# from django.db.models import Q

# from .models import ServiceType, CustomerMotorcycle, ServiceBooking
# from inventory.models import Motorcycle
# from users.models import User
# # Import the BlockedServiceDate model from the dashboard app
# from dashboard.models import BlockedServiceDate
# # Import SiteSettings from dashboard for time slot generation
# from dashboard.models import SiteSettings, ServiceBrand
# from datetime import timedelta, time


# # Abstract base form for common service booking fields
# # Kept appointment_date and booking_comments here as they are used in Admin forms
# class BaseAdminServiceBookingForm(forms.Form):
#     service_type = forms.ModelChoiceField(
#         queryset=ServiceType.objects.filter(is_active=True),
#         empty_label="-- Select Service Type --",
#         label="Service Type",
#         widget=forms.Select(attrs={'class': 'form-control'}),
#         required=True
#     )
#     appointment_date = forms.DateTimeField(
#         label="Preferred Date and Time",
#         widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
#         required=True
#     )
#     booking_comments = forms.CharField(
#         widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
#         required=False,
#         label="Comments or specific requests"
#     )


# # --- Admin Booking Forms ---

# # Form for creating a service booking for an anonymous/one-off customer
# class AdminAnonBookingForm(BaseAdminServiceBookingForm):
#     # One-off Customer Details
#     one_off_first_name = forms.CharField(
#         max_length=100,
#         label="First Name",
#         widget=forms.TextInput(attrs={'class': 'form-control'}),
#         required=True
#     )
#     one_off_last_name = forms.CharField(
#         max_length=100,
#         label="Last Name",
#         widget=forms.TextInput(attrs={'class': 'form-control'}),
#         required=True
#     )
#     one_off_email = forms.EmailField(
#         label="Email",
#         widget=forms.EmailInput(attrs={'class': 'form-control'}),
#         required=False,
#     )
#     one_off_phone_number = forms.CharField(
#         max_length=20,
#         required=False,
#         label="Phone Number",
#         widget=forms.TextInput(attrs={'class': 'form-control'})
#     )
#     anon_customer_address = forms.CharField(
#         widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
#         required=False,
#         label="Address"
#     )


#     # Anonymous Vehicle Details
#     anon_vehicle_make = forms.CharField(
#         max_length=100,
#         label="Make",
#         widget=forms.TextInput(attrs={'class': 'form-control'}),
#         required=True
#     )
#     anon_vehicle_model = forms.CharField(
#         max_length=100,
#         label="Model",
#         widget=forms.TextInput(attrs={'class': 'form-control'}),
#         required=True
#     )
#     anon_vehicle_year = forms.IntegerField(
#         label="Year",
#         widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1900', 'max': datetime.date.today().year}),
#         required=False,
#     )
#     anon_vehicle_rego = forms.CharField(
#         max_length=20,
#         required=False,
#         label="Registration",
#         widget=forms.TextInput(attrs={'class': 'form-control'})
#     )
#     anon_vehicle_vin_number = forms.CharField(
#         max_length=50,
#         required=False,
#         label="VIN",
#         widget=forms.TextInput(attrs={'class': 'form-control'})
#     )
#     anon_vehicle_odometer = forms.IntegerField(
#         required=False,
#         label="Odometer",
#         widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '0'})
#     )
#     anon_vehicle_transmission = forms.ChoiceField(
#         choices=[('', '---------')] + list(Motorcycle.TRANSMISSION_CHOICES),
#         required=False,
#         label="Transmission",
#         widget=forms.Select(attrs={'class': 'form-control'})
#     )
#     anon_engine_number = forms.CharField(
#         max_length=50,
#         required=False,
#         label="Engine Number",
#         widget=forms.TextInput(attrs={'class': 'form-control'})
#     )


#     # Clean method for the form
#     def clean(self):
#         cleaned_data = super().clean()
#         return cleaned_data



# # Form for creating a service booking for an existing registered user
# class AdminUserBookingForm(BaseAdminServiceBookingForm):
#     user = forms.ModelChoiceField(
#         queryset=User.objects.filter(is_active=True).order_by('first_name', 'last_name'),
#         empty_label="-- Select Existing Customer --",
#         label="Existing Customer",
#         widget=forms.Select(attrs={'class': 'form-control'}),
#         required=True
#     )

#     # Fields to optionally update user details (kept as required=False as per existing code)
#     user_first_name = forms.CharField(
#         max_length=100,
#         required=False,
#         label="Update First Name",
#         widget=forms.TextInput(attrs={'class': 'form-control'})
#     )
#     user_last_name = forms.CharField(
#         max_length=100,
#         required=False,
#         label="Update Last Name",
#         widget=forms.TextInput(attrs={'class': 'form-control'})
#     )
#     user_email = forms.EmailField(
#         required=False,
#         label="Update Email",
#         widget=forms.EmailInput(attrs={'class': 'form-control'})
#     )
#     user_phone_number = forms.CharField(
#         max_length=20,
#         required=False,
#         label="Update Phone Number",
#         widget=forms.TextInput(attrs={'class': 'form-control'})
#     )

#     # Choices for bike selection type
#     BIKE_SELECTION_CHOICES = [
#         ('existing', 'Select Existing Motorcycle'),
#         ('new', 'Add New Motorcycle'),
#     ]
#     bike_selection_type = forms.ChoiceField(
#         choices=BIKE_SELECTION_CHOICES,
#         widget=forms.RadioSelect,
#         initial='existing',
#         label="Motorcycle Options",
#         required=True
#     )

#     existing_motorcycle = forms.ModelChoiceField(
#         queryset=CustomerMotorcycle.objects.none(),
#         required=False,
#         label="Existing Motorcycle",
#         widget=forms.Select(attrs={'class': 'form-control'})
#     )

#     # Fields for adding a new motorcycle (Required is handled in clean method based on bike_selection_type)
#     new_bike_make = forms.CharField(
#         max_length=100,
#         required=False,
#         label="Make",
#         widget=forms.TextInput(attrs={'class': 'form-control'})
#     )
#     new_bike_model = forms.CharField(
#         max_length=100,
#         required=False,
#         label="Model",
#         widget=forms.TextInput(attrs={'class': 'form-control'})
#     )
#     new_bike_year = forms.IntegerField(
#         required=False,
#         label="Year",
#         widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1900', 'max': datetime.date.today().year})
#     )
#     new_bike_rego = forms.CharField(
#         max_length=20,
#         required=False,
#         label="Registration",
#         widget=forms.TextInput(attrs={'class': 'form-control'})
#     )
#     new_bike_vin_number = forms.CharField(
#         max_length=50,
#         required=False,
#         label="VIN Number",
#         widget=forms.TextInput(attrs={'class': 'form-control'})
#     )
#     new_bike_odometer = forms.IntegerField(
#         required=False,
#         label="Odometer",
#         widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '0'})
#     )
#     new_bike_transmission = forms.ChoiceField(
#         choices=[('', '---------')] + list(Motorcycle.TRANSMISSION_CHOICES),
#         required=False,
#         label="Transmission",
#         widget=forms.Select(attrs={'class': 'form-control'})
#     )

#     # Initialize form to populate existing motorcycle queryset
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         user_id = None
#         if 'user' in self.data:
#             try:
#                 user_id = int(self.data['user'])
#             except (ValueError, TypeError):
#                 pass
#         elif self.initial.get('user'):
#              user_id = self.initial['user'].id if isinstance(self.initial['user'], User) else self.initial['user']

#         if user_id:
#             try:
#                 user = User.objects.get(id=user_id)
#                 self.fields['existing_motorcycle'].queryset = CustomerMotorcycle.objects.filter(owner=user).order_by('make', 'model')
#             except User.DoesNotExist:
#                 pass

#     # Clean method with conditional validation
#     def clean(self):
#         cleaned_data = super().clean()
#         user = cleaned_data.get('user')
#         bike_selection_type = cleaned_data.get('bike_selection_type')
#         existing_motorcycle = cleaned_data.get('existing_motorcycle')
#         new_bike_make = cleaned_data.get('new_bike_make')
#         new_bike_model = cleaned_data.get('new_bike_model')
#         new_bike_year = cleaned_data.get('new_bike_year')

#         # The 'user' field is now required at the field level, but we keep this check
#         # for clarity and consistency with existing logic.
#         if not user:
#             self.add_error('user', 'Please select an existing customer.')

#         # Validate bike selection based on type
#         if bike_selection_type == 'existing':
#             if not existing_motorcycle:
#                 self.add_error('existing_motorcycle', 'Please select an existing motorcycle.')
#             # Ensure new bike fields are empty - this validation remains
#             if new_bike_make or new_bike_model or new_bike_year is not None:
#                  self.add_error(None, 'New bike details should not be provided when selecting an existing bike.')

#         elif bike_selection_type == 'new':
#             # These fields are now explicitly required by the user's request
#             if not new_bike_make:
#                 self.add_error('new_bike_make', 'Make is required for a new motorcycle.')
#             if not new_bike_model:
#                 self.add_error('new_bike_model', 'Model is required for a new motorcycle.')
#             if not new_bike_year:
#                 self.add_error('new_bike_year', 'Year is required for a new motorcycle.')
#             # Ensure existing motorcycle field is empty - this validation remains
#             if existing_motorcycle:
#                  self.add_error('existing_motorcycle', 'Cannot select an existing motorcycle when adding a new one.')

#         return cleaned_data

# # Form for basic service details (frontend customer form - Step 1)
# class ServiceDetailsForm(forms.Form):
#     service_type = forms.ModelChoiceField(
#         queryset=ServiceType.objects.filter(is_active=True),
#         empty_label="Select a Service Type",
#         label="Service Type",
#         widget=forms.Select(attrs={'class': 'form-control'}),
#         required=True
#     )
#     dropoff_date = forms.DateField(
#         label="Preferred Date",
#         # We will use Flatpickr for the date input in the template
#         widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'text'}), 
#         required=True
#     )
#     # Added a ChoiceField for dropoff time
#     dropoff_time = forms.ChoiceField(
#         label="Preferred Drop-off Time",
#         choices=[], # Choices will be populated dynamically in the view
#         widget=forms.Select(attrs={'class': 'form-control'}),
#         required=True
#     )

#     # Add a clean method to validate that a time slot was selected
#     def clean(self):
#         cleaned_data = super().clean()
#         # Check if a drop_off_time was provided.
#         # The choices are populated in the view, so we just check if a value was selected.
#         drop_off_time = cleaned_data.get('drop_off_time')
#         if not drop_off_time:
#              self.add_error('drop_off_time', 'Please select a valid drop-off time.')

#         # Add any other necessary cross-field validation here
#         return cleaned_data

# class CustomerMotorcycleForm(forms.ModelForm):
#     # Change 'make' from ModelChoiceField to a CharField with a Select widget
#     # We will populate the choices dynamically in __init__
#     make = forms.CharField(
#         label="Make",
#         widget=forms.Select(attrs={'class': 'form-control'}),
#         required=True,
#         help_text="Due to part availability, we can only service the brands available in this drop down menu."
#     )

#     class Meta:
#         model = CustomerMotorcycle
#         fields = ['make', 'model', 'year', 'rego', 'odometer', 'vin_number', 'transmission']
#         widgets = {
#             'transmission': forms.Select(choices=Motorcycle.TRANSMISSION_CHOICES, attrs={'class': 'form-control'}),
#             'year': forms.NumberInput(attrs={'class': 'form-control', 'min': '1900', 'max': datetime.date.today().year}),
#             'odometer': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
#             'rego': forms.TextInput(attrs={'class': 'form-control'}),
#             'vin_number': forms.TextInput(attrs={'class': 'form-control'}),
#             'model': forms.TextInput(attrs={'class': 'form-control'}),
#         }

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)

#         # Get the list of valid service brand names
#         valid_brand_names = list(ServiceBrand.objects.all().order_by('name').values_list('name', flat=True))

#         # Create choices list for the 'make' CharField
#         # Each choice is a tuple (value, label)
#         brand_choices = [(name, name) for name in valid_brand_names]

#         # Add the empty label option at the beginning
#         choices_with_empty = [('', '--- Select Make ---')] + brand_choices

#         # If this form is bound to an existing instance
#         if self.instance and self.instance.pk:
#             current_make = self.instance.make
#             # If the instance's make is NOT in the list of valid brands,
#             # add it to the choices so it appears selected in the dropdown.
#             # We add it at the top after the empty choice for visibility,
#             # but it could technically be anywhere.
#             if current_make and current_make not in valid_brand_names:
#                  # Ensure it's not already added if instance.make was empty string etc.
#                  if (current_make, current_make) not in choices_with_empty:
#                      choices_with_empty.insert(1, (current_make, f"{current_make} (Not a standard service brand)")) # Optional: add a label suffix

#         # Set the choices for the 'make' field
#         self.fields['make'].widget.choices = choices_with_empty


#     # Override the clean_make method for custom validation
#     def clean_make(self):
#         submitted_make_name = self.cleaned_data.get('make')

#         # Handle empty value if somehow passed despite required=True (defensive)
#         if not submitted_make_name:
#             raise forms.ValidationError("This field is required.")

#         # Get the list of valid brand names (case-insensitive comparison is safer)
#         valid_brand_names_lower = {brand.name.lower() for brand in ServiceBrand.objects.all()}
#         submitted_make_lower = submitted_make_name.lower()

#         # Case 1: Form is for an existing instance (updating)
#         if self.instance and self.instance.pk:
#             initial_make_name = self.instance.make # Get the original value from the instance

#             # Check if the submitted value is the same as the original instance value (case-insensitive)
#             # This allows keeping the original, potentially out-of-list value.
#             if submitted_make_lower == initial_make_name.lower():
#                 # Return the original name exactly as it was (or the submitted name, which should be the same case-insensitively)
#                 # Returning the submitted name is generally fine here.
#                 return submitted_make_name

#             # If the submitted value is *different* from the original instance value,
#             # it must be one of the valid brands.
#             if submitted_make_lower not in valid_brand_names_lower:
#                 # The user tried to change the make to something that isn't in the valid list
#                 raise forms.ValidationError("You can only select a make from the available list or keep the original value.")
#             else:
#                  # The user selected a *different* make, and it is in the valid list.
#                  # Find the ServiceBrand object to return the canonical name (correct casing)
#                  canonical_brand = ServiceBrand.objects.get(name__iexact=submitted_make_name)
#                  return canonical_brand.name

#         # Case 2: Form is for a new instance (creating)
#         else: # self.instance is None or has no pk
#              # The submitted make must be one of the valid brands.
#              if submitted_make_lower not in valid_brand_names_lower:
#                  raise forms.ValidationError("Please select a valid motorcycle make from the list.")
#              else:
#                  # A valid brand was selected. Find the ServiceBrand object to return canonical name.
#                  canonical_brand = ServiceBrand.objects.get(name__iexact=submitted_make_name)
#                  return canonical_brand.name

#     # Keep your existing clean methods as they are now part of the CharField logic
#     def clean_rego(self):
#          if self.cleaned_data.get('rego'):
#              return self.cleaned_data['rego'].upper()
#          return self.cleaned_data.get('rego')

#     def clean_vin_number(self):
#          return self.cleaned_data.get('vin_number')


# # Form for service booking by an existing user (Step 3)
# class ServiceBookingUserForm(forms.Form):
#     first_name = forms.CharField(
#         max_length=100,
#         widget=forms.TextInput(attrs={'class': 'form-control'}),
#         required=True
#     )
#     last_name = forms.CharField(
#         max_length=100,
#         widget=forms.TextInput(attrs={'class': 'form-control'}),
#         required=True
#     )
#     email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}), required=True)
#     phone_number = forms.CharField(max_length=20, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
#     preferred_contact = forms.ChoiceField(
#         choices=ServiceBooking.CONTACT_CHOICES,
#         widget=forms.RadioSelect,
#         initial='email',
#         label="Preferred method of contact",
#         required=True
#     )
#     booking_comments = forms.CharField(
#         widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
#         required=False,
#         label="Comments or specific requests"
#     )

# # Form to select an existing customer motorcycle (no changes requested on required fields)
# class ExistingCustomerMotorcycleForm(forms.Form):
#     motorcycle = forms.ModelChoiceField(
#         queryset=CustomerMotorcycle.objects.none(),
#         label="Select your Motorcycle",
#         widget=forms.Select(attrs={'class': 'form-control'}),
#         required=True
#     )

#     # Initialize form with user's motorcycles
#     def __init__(self, *args, **kwargs):
#         user = kwargs.pop('user', None)
#         super().__init__(*args, **kwargs)
#         if user and user.is_authenticated:
#             self.fields['motorcycle'].queryset = CustomerMotorcycle.objects.filter(owner=user)