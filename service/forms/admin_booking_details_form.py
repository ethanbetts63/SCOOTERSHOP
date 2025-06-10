# service/forms.py (or service/admin_forms.py)

from django import forms
from service.models import ServiceType, ServiceBooking # Import ServiceBooking to get PAYMENT_STATUS_CHOICES
from django.utils.translation import gettext_lazy as _
from datetime import date
from django.utils import timezone

class AdminBookingDetailsForm(forms.Form):
    """
    Form for admins to select service details, dates, times, add notes,
    and set initial payment status for a new service booking.

    Validation is designed to provide warnings rather than blocking submission,
    allowing admins to override typical user-facing restrictions.
    """
    service_type = forms.ModelChoiceField(
        queryset=ServiceType.objects.filter(is_active=True).order_by('name'),
        empty_label=_("Select a Service Type"),
        label=_("Service Type"),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )

    service_date = forms.DateField(
        label=_("Service Date"),
        widget=forms.DateInput(attrs={'class': 'form-control flatpickr-admin-date-input', 'placeholder': 'Select service date'}),
        required=True,
        help_text=_("The requested date for the service to be performed.")
    )

    dropoff_date = forms.DateField(
        label=_("Preferred Drop-off Date"),
        widget=forms.DateInput(attrs={'class': 'form-control flatpickr-admin-date-input', 'placeholder': 'Select drop-off date'}),
        required=True,
        help_text=_("The date the motorcycle will be dropped off for service.")
    )

    dropoff_time = forms.TimeField(
        label=_("Preferred Drop-off Time"),
        # Use a text input for flexibility, JS will populate/validate
        widget=forms.TextInput(attrs={'class': 'form-control flatpickr-admin-time-input', 'placeholder': 'Select drop-off time'}),
        required=True,
        help_text=_("The preferred time of day for motorcycle drop-off (e.g., 09:00, 14:30).")
    )

    # Allow admin to set initial booking status directly
    booking_status = forms.ChoiceField(
        label=_("Initial Booking Status"),
        choices=ServiceBooking.BOOKING_STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True,
        initial='pending', # Default to pending confirmation for admin bookings
        help_text=_("Set the initial status of this booking.")
    )

    # Allow admin to set initial payment status directly
    payment_status = forms.ChoiceField(
        label=_("Initial Payment Status"),
        choices=ServiceBooking.PAYMENT_STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True,
        initial='unpaid', # Default to unpaid for admin bookings
        help_text=_("Set the initial payment status for this booking.")
    )

    customer_notes = forms.CharField(
        label=_("Customer Notes (Optional)"),
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False,
        help_text=_("Any additional notes or requests from the customer.")
    )

    admin_notes = forms.CharField(
        label=_("Internal Admin Notes (Optional)"),
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False,
        help_text=_("Internal notes for staff, not visible to the customer.")
    )

    # Fields for estimated pickup date - purely for admin tracking
    estimated_pickup_date = forms.DateField(
        label=_("Estimated Pickup Date (Optional)"),
        widget=forms.DateInput(attrs={'class': 'form-control flatpickr-admin-date-input', 'placeholder': 'Estimated pickup date'}),
        required=False,
        help_text=_("Estimated date when the customer can pick up the motorcycle.")
    )


    def clean(self):
        """
        Custom clean method for cross-field validation with warnings.
        """
        cleaned_data = super().clean()
        service_date = cleaned_data.get('service_date')
        dropoff_date = cleaned_data.get('dropoff_date')
        dropoff_time = cleaned_data.get('dropoff_time')

        # This list will store non-blocking warning messages for the admin
        self._warnings = []

        if not all([service_date, dropoff_date, dropoff_time]):
            # If basic date/time fields are missing, let individual field errors handle it.
            return cleaned_data

        # --- Validation as Warnings for Admin ---

        # Warning 1: Drop-off date after service date
        if dropoff_date > service_date:
            self._warnings.append(_("Warning: Drop-off date is after the service date."))

        # Warning 2: Service date in the past
        if service_date < date.today():
            self._warnings.append(_("Warning: Service date is in the past."))

        # Warning 3: Drop-off date in the past
        if dropoff_date < date.today():
            self._warnings.append(_("Warning: Drop-off date is in the past."))

        # Warning 4: Drop-off time in the past for today's drop-off
        if dropoff_date == date.today() and dropoff_time < timezone.localtime(timezone.now()).time():
            self._warnings.append(_("Warning: Drop-off time for today is in the past."))

        return cleaned_data

    def get_warnings(self):
        """
        Returns a list of non-blocking warning messages generated during clean.
        """
        return getattr(self, '_warnings', [])

