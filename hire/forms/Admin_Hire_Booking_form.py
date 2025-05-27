# hire/forms/Admin_Hire_Booking_form.py
from django import forms
from django.core.exceptions import ValidationError
from django.forms import ModelChoiceField, RadioSelect
import datetime

# Import models
from inventory.models import Motorcycle
from ..models import AddOn, Package, DriverProfile, BookingAddOn
from ..models.hire_booking import STATUS_CHOICES, PAYMENT_STATUS_CHOICES, PAYMENT_METHOD_CHOICES, HireBooking
# Import pricing utility
from hire.hire_pricing import calculate_addon_price # Import the new pricing function

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
    # NEW FIELD: Booked Hourly Rate
    booked_hourly_rate = forms.DecimalField(
        max_digits=8, decimal_places=2,
        label="Booked Hourly Rate",
        required=True,
        help_text="This will prefill from the motorcycle's hourly rate, or the general hourly default. Used for same-day bookings. (e.g., 25.00)"
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
        required=False, # Changed to False to allow custom validation in clean()
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
        # Pop the instance if it exists
        instance = kwargs.pop('instance', None)
        # Pop hire_settings for pricing calculations
        self.hire_settings = kwargs.pop('hire_settings', None)
        super().__init__(*args, **kwargs)

        # Set queryset and label for motorcycle
        self.fields['motorcycle'].queryset = Motorcycle.objects.filter(is_available=True, conditions__name='hire').distinct()
        self.fields['motorcycle'].label_from_instance = lambda obj: f"ID: {obj.id} - {obj.brand} {obj.model} ({obj.year})"

        # Set queryset for packages
        self.available_packages = Package.objects.filter(is_available=True)
        self.fields['package'].queryset = self.available_packages
        # Updated label_from_instance for package to show name and new pricing fields
        self.fields['package'].label_from_instance = lambda obj: f"{obj.name} (Daily: {obj.daily_cost:.2f}, Hourly: {obj.hourly_cost:.2f})"


        # Dynamically create add-on fields
        # Fetch ALL add-ons, not just available ones, for admin purposes
        self.available_addons = AddOn.objects.all() # Changed from .filter(is_available=True)
        self.display_addons = [] # This will hold addon info for rendering in the template
        
        # Store selected add-ons and their quantities from the instance
        selected_addons_from_instance = {}
        if instance:
            # CORRECTED: Use the related_name 'booking_addons' instead of 'bookingaddon_set'
            for booking_addon in instance.booking_addons.all():
                selected_addons_from_instance[booking_addon.addon.id] = booking_addon.quantity

        for addon in self.available_addons:
            is_selected = addon.id in selected_addons_from_instance
            quantity = selected_addons_from_instance.get(addon.id, 1) # Default to 1 if selected but no quantity

            self.display_addons.append({
                'addon': addon,
                'adjusted_max_quantity': addon.max_quantity, # For admin, no package-based adjustment needed
                'is_included_in_package': False # Always false for admin form's display logic
            })

            # Create fields for each addon
            self.fields[f'addon_{addon.id}_selected'] = forms.BooleanField(
                required=False,
                label=addon.name,
                initial=is_selected, # Set initial based on instance
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
                initial=quantity, # Set initial based on instance
                widget=forms.NumberInput(attrs={
                    'class': 'addon-quantity',
                    # Show if selected, otherwise hidden by default
                    'style': 'display: block;' if is_selected and addon.max_quantity > 1 else 'display: none;'
                }),
                required=False
            )

        # Set queryset and label for driver profile
        self.fields['driver_profile'].queryset = DriverProfile.objects.all().order_by('name')
        self.fields['driver_profile'].label_from_instance = lambda obj: f"ID: {obj.id} - {obj.name} ({obj.email})"

        # If an instance is provided, populate initial form data
        if instance:
            self.fields['pick_up_date'].initial = instance.pickup_date
            self.fields['pick_up_time'].initial = instance.pickup_time
            self.fields['return_date'].initial = instance.return_date
            self.fields['return_time'].initial = instance.return_time
            self.fields['motorcycle'].initial = instance.motorcycle
            self.fields['booked_daily_rate'].initial = instance.booked_daily_rate
            self.fields['booked_hourly_rate'].initial = instance.booked_hourly_rate
            self.fields['package'].initial = instance.package
            self.fields['driver_profile'].initial = instance.driver_profile
            self.fields['currency'].initial = instance.currency
            self.fields['total_price'].initial = instance.total_price
            self.fields['payment_method'].initial = instance.payment_method
            self.fields['payment_status'].initial = instance.payment_status
            self.fields['status'].initial = instance.status
            self.fields['internal_notes'].initial = instance.internal_notes


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
                    # Calculate the actual price of the add-on using the new pricing logic
                    # Ensure all necessary parameters for calculate_addon_price are available
                    if all([addon, quantity, pickup_date, return_date, pickup_time, return_time, self.hire_settings]):
                        calculated_addon_price = calculate_addon_price(
                            addon_instance=addon,
                            quantity=quantity,
                            pickup_date=pickup_date,
                            return_date=return_date,
                            pickup_time=pickup_time,
                            return_time=return_time,
                            hire_settings=self.hire_settings
                        )
                        selected_addons_data.append({
                            'addon': addon,
                            'quantity': quantity,
                            'price': calculated_addon_price # Store the calculated price
                        })
                    else:
                        # If pricing parameters are missing, add an error
                        form_errors[f'addon_{addon.id}_selected'] = "Cannot calculate add-on price due to missing booking details or hire settings."

        cleaned_data['selected_addons_data'] = selected_addons_data # Store for view/save

        # --- Section 5: Financial Details Validation ---
        total_price = cleaned_data.get('total_price')
        if total_price is not None and total_price < 0:
            form_errors['total_price'] = "Total price cannot be negative."

        payment_status = cleaned_data.get('payment_status')
        if payment_status == 'paid' and (total_price is None or total_price <= 0):
            form_errors['total_price'] = "Total price must be greater than 0 if payment status is 'Fully Paid'."

        # --- Section 2: Booked Rates Validation ---
        booked_daily_rate = cleaned_data.get('booked_daily_rate')
        booked_hourly_rate = cleaned_data.get('booked_hourly_rate')

        if booked_daily_rate is not None and booked_daily_rate < 0:
            form_errors['booked_daily_rate'] = "Booked daily rate cannot be negative."
        if booked_hourly_rate is not None and booked_hourly_rate < 0: # Added validation for hourly rate
            form_errors['booked_hourly_rate'] = "Booked hourly rate cannot be negative."


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
