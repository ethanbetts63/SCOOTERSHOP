# hire/forms/Admin_Hire_Booking_form.py
from django import forms
from django.core.exceptions import ValidationError
from django.forms import ModelChoiceField, RadioSelect
import datetime

# Import models
from inventory.models import Motorcycle
from ..models import AddOn, Package, DriverProfile
from ..models.hire_booking import STATUS_CHOICES, PAYMENT_STATUS_CHOICES, PAYMENT_METHOD_CHOICES, HireBooking
# No direct import of HireSettings here, it will be used in the view for default rates if needed.

class AdminHireBookingForm(forms.Form):
    """
    A single-page admin form for creating HireBooking records directly.
    Bypasses the multi-step customer booking flow and allows for overrides.
    """

    # Section 1: Date & Time Selection
    pick_up_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label="Pick Up Date",
        required=True
    )
    # Changed to TimeInput for native time picker
    pick_up_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        label="Pick Up Time",
        required=True
    )
    return_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label="Return Date",
        required=True
    )
    # Changed to TimeInput for native time picker
    return_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        label="Return Time",
        required=True
    )

    # Section 2: Motorcycle Selection & Rates
    motorcycle = forms.ModelChoiceField(
        queryset=Motorcycle.objects.none(), # Will be set in __init__
        label="Motorcycle",
        required=True,
        empty_label="--- Select a Motorcycle ---"
    )
    booked_daily_rate = forms.DecimalField(
        max_digits=8, decimal_places=2,
        label="Booked Daily Rate",
        required=True,
        help_text="This will prefill from the motorcycle's default, or the general daily default, but can be overridden. (e.g., 150.00)"
    )

    # Section 3: Add-ons & Packages
    package = forms.ModelChoiceField(
        queryset=Package.objects.none(), # Will be set in __init__
        # Changed widget from RadioSelect to Select for dropdown
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False,
        label="Select a Package",
        empty_label="--- No Package ---"
    )
    # Add-on fields will be dynamically added in __init__

    # Section 4: Driver Profile Selection
    driver_profile = forms.ModelChoiceField(
        queryset=DriverProfile.objects.none(), # Will be set in __init__
        label="Driver Profile",
        required=True,
        empty_label="--- Select a Driver Profile ---"
    )

    # Section 5: Financial Details & Status
    currency = forms.CharField(
        max_length=3,
        initial='AUD',
        label="Currency Code (e.g., AUD, USD)",
        required=True
    )
    total_price = forms.DecimalField(
        max_digits=10, decimal_places=2,
        label="Admin Entered Total Price",
        required=True,
        help_text="Enter the final total price. An estimated total will be calculated dynamically on the page."
    )
    payment_method = forms.ChoiceField(
        choices=PAYMENT_METHOD_CHOICES,
        label="Payment Method",
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    payment_status = forms.ChoiceField(
        choices=PAYMENT_STATUS_CHOICES,
        label="Payment Status",
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        label="Booking Status",
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    # Section 6: Internal Notes
    internal_notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        label="Internal Notes",
        required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Removed time_choices population as we are now using native time input type='time'
        # The browser will handle the time selection UI for pick_up_time and return_time.

        # Set queryset and label for motorcycle
        self.fields['motorcycle'].queryset = Motorcycle.objects.filter(is_available=True, conditions__name='hire').distinct()
        self.fields['motorcycle'].label_from_instance = lambda obj: f"ID: {obj.id} - {obj.brand} {obj.model} ({obj.year})"

        # Set queryset for packages
        self.available_packages = Package.objects.filter(is_available=True)
        self.fields['package'].queryset = self.available_packages
        # Updated label_from_instance for package to show name and price
        self.fields['package'].label_from_instance = lambda obj: f"{obj.name} ({obj.package_price:.2f})"


        # Dynamically create add-on fields
        self.available_addons = AddOn.objects.filter(is_available=True)
        self.display_addons = [] # This will hold addon info for rendering in the template
        for addon in self.available_addons:
            self.display_addons.append({
                'addon': addon,
                'adjusted_max_quantity': addon.max_quantity, # For admin, no package-based adjustment needed
                'is_included_in_package': False # Always false for admin form's display logic
            })

            # Create fields for each addon
            self.fields[f'addon_{addon.id}_selected'] = forms.BooleanField(
                required=False,
                label=addon.name,
                widget=forms.CheckboxInput(attrs={
                    'class': 'addon-checkbox',
                    'data-addon-id': str(addon.id),
                    'data-original-max-quantity': str(addon.max_quantity),
                    'data-min-quantity': str(addon.min_quantity),
                    'data-adjusted-max-quantity': str(addon.max_quantity) # Pass adjusted max to JS
                })
            )
            self.fields[f'addon_{addon.id}_quantity'] = forms.IntegerField(
                min_value=addon.min_quantity,
                max_value=addon.max_quantity,
                initial=1,
                widget=forms.NumberInput(attrs={
                    'class': 'addon-quantity',
                    'style': 'display: none;' # Hidden by default, shown by JS if selected
                }),
                required=False
            )

        # Set queryset and label for driver profile
        self.fields['driver_profile'].queryset = DriverProfile.objects.all().order_by('name')
        self.fields['driver_profile'].label_from_instance = lambda obj: f"ID: {obj.id} - {obj.name} ({obj.email})"


    def clean(self):
        cleaned_data = super().clean()

        # Initialize an errors dictionary to collect all validation errors
        form_errors = {}

        # --- Section 1: Date & Time Validation ---
        pickup_date = cleaned_data.get('pick_up_date')
        pickup_time = cleaned_data.get('pick_up_time')
        return_date = cleaned_data.get('return_date')
        return_time = cleaned_data.get('return_time')

        pickup_datetime = None
        return_datetime = None

        if pickup_date and pickup_time:
            pickup_datetime = datetime.datetime.combine(pickup_date, pickup_time)
        if return_date and return_time:
            return_datetime = datetime.datetime.combine(return_date, return_time)

        if pickup_datetime and return_datetime:
            if return_datetime <= pickup_datetime:
                form_errors['return_date'] = "Return date and time must be after pickup date and time."
                form_errors['return_time'] = "Return date and time must be after pickup date and time."

        # --- Section 3: Add-ons & Packages Processing ---
        selected_package_from_form = cleaned_data.get('package')
        cleaned_data['selected_package_instance'] = selected_package_from_form # Store the package object for view/save

        selected_addons_data = []
        for addon_info in self.display_addons:
            addon = addon_info['addon']
            is_selected = cleaned_data.get(f'addon_{addon.id}_selected')
            quantity = cleaned_data.get(f'addon_{addon.id}_quantity', 0)

            if is_selected:
                # Re-validate quantity based on adjusted_max_quantity (which is just max_quantity for admin form)
                adjusted_max_quantity_for_validation = addon_info['adjusted_max_quantity']
                if quantity < addon.min_quantity or quantity > adjusted_max_quantity_for_validation:
                    form_errors[f'addon_{addon.id}_quantity'] = (
                        f"Quantity for {addon.name} must be between {addon.min_quantity}-{adjusted_max_quantity_for_validation}."
                    )
                else:
                    selected_addons_data.append({
                        'addon': addon,
                        'quantity': quantity,
                        'price': addon.cost # Capture the current cost of the addon
                    })
        cleaned_data['selected_addons_data'] = selected_addons_data # Store for view/save

        # --- Section 5: Financial Details Validation ---
        total_price = cleaned_data.get('total_price')
        if total_price is not None and total_price < 0:
            form_errors['total_price'] = "Total price cannot be negative."

        payment_status = cleaned_data.get('payment_status')
        if payment_status == 'paid' and (total_price is None or total_price <= 0):
            form_errors['total_price'] = "Total price must be greater than 0 if payment status is 'Fully Paid'."

        # If any errors were collected, add them to the form's errors
        if form_errors:
            for field, message in form_errors.items():
                # For non-field errors, field will be None
                if field is None:
                    self.add_error(None, ValidationError(message))
                else:
                    self.add_error(field, ValidationError(message))
            # Raise ValidationError to prevent saving if there are errors
            raise ValidationError("Please correct the errors below.")

        return cleaned_data

    def get_addon_fields(self):
        """Helper to iterate through add-on fields for the template."""
        # This helper is for the template to easily loop through addon fields
        for addon_info in self.display_addons:
            addon = addon_info['addon']
            # Ensure the fields were actually created for this addon
            if f'addon_{addon.id}_selected' in self.fields:
                yield {
                    'addon': addon,
                    'selected_field': self[f'addon_{addon.id}_selected'],
                    'quantity_field': self[f'addon_{addon.id}_quantity']
                }
