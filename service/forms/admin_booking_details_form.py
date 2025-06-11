# service/forms.py (or service/admin_forms.py)

from django import forms
from service.models import ServiceBooking, ServiceType
from django.utils.translation import gettext_lazy as _
from datetime import date
from django.utils import timezone

class AdminBookingDetailsForm(forms.ModelForm):
    """
    Form for admins to create and update service booking details.
    This is now a ModelForm to handle both creation and editing of ServiceBooking instances.
    """
    class Meta:
        model = ServiceBooking
        fields = [
            'service_type',
            'service_date',
            'dropoff_date',
            'dropoff_time',
            'booking_status',
            'payment_status',
            'customer_notes',
            'estimated_pickup_date',
        ]
        widgets = {
            'service_type': forms.Select(attrs={'class': 'form-control'}),
            'service_date': forms.DateInput(attrs={'class': 'form-control flatpickr-admin-date-input', 'placeholder': 'Select service date'}),
            'dropoff_date': forms.DateInput(attrs={'class': 'form-control flatpickr-admin-date-input', 'placeholder': 'Select drop-off date'}),
            'dropoff_time': forms.TextInput(attrs={'class': 'form-control flatpickr-admin-time-input', 'placeholder': 'Select drop-off time'}),
            'booking_status': forms.Select(attrs={'class': 'form-control'}),
            'payment_status': forms.Select(attrs={'class': 'form-control'}),
            'customer_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'estimated_pickup_date': forms.DateInput(attrs={'class': 'form-control flatpickr-admin-date-input', 'placeholder': 'Estimated pickup date'}),
        }
        labels = {
            'service_type': _("Service Type"),
            'service_date': _("Service Date"),
            'dropoff_date': _("Preferred Drop-off Date"),
            'dropoff_time': _("Preferred Drop-off Time"),
            'booking_status': _("Booking Status"),
            'payment_status': _("Payment Status"),
            'customer_notes': _("Customer Notes (Optional)"),
            'estimated_pickup_date': _("Estimated Pickup Date"),
        }
        help_texts = {
            'service_date': _("The requested date for the service to be performed."),
            'dropoff_date': _("The date the motorcycle will be dropped off for service."),
            'dropoff_time': _("The preferred time of day for motorcycle drop-off (e.g., 09:00, 14:30)."),
            'booking_status': _("Set the status of this booking."),
            'payment_status': _("Set the payment status for this booking."),
            'customer_notes': _("Any additional notes or requests from the customer."),
            'estimated_pickup_date': _("Estimated date when the customer can pick up the motorcycle. Prefilled based on service type duration."),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['service_type'].queryset = ServiceType.objects.filter(is_active=True).order_by('name')
        self.fields['service_type'].empty_label = _("Select a Service Type")

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
        if dropoff_date == date.today() and hasattr(dropoff_time, 'hour') and dropoff_time < timezone.localtime(timezone.now()).time():
            self._warnings.append(_("Warning: Drop-off time for today is in the past."))

        return cleaned_data

    def get_warnings(self):
        """
        Returns a list of non-blocking warning messages generated during clean.
        """
        return getattr(self, '_warnings', [])
