# payments/forms/admin_refund_request_form.py

from django import forms
from django.core.exceptions import ValidationError
from payments.models.RefundRequest import RefundRequest
from hire.models import HireBooking
from service.models import ServiceBooking
from inventory.models import SalesBooking # Import SalesBooking
from decimal import Decimal

class AdminRefundRequestForm(forms.ModelForm):
    """
    Form for administrators to create or edit a RefundRequest.
    Allows selection of either a HireBooking, ServiceBooking, or SalesBooking,
    and input of reason, staff notes, and amount to refund.
    Customer profiles and payment are automatically linked
    from the selected booking.
    """
    # Fields for selecting a booking type
    hire_booking = forms.ModelChoiceField(
        queryset=HireBooking.objects.filter(payment_status__in=['paid', 'deposit_paid', 'refunded']),
        label="Select Hire Booking",
        help_text="Choose a Hire Booking (Paid, Deposit Paid, or Refunded status).",
        required=False
    )
    service_booking = forms.ModelChoiceField(
        queryset=ServiceBooking.objects.filter(payment_status__in=['paid', 'deposit_paid', 'refunded']),
        label="Select Service Booking",
        help_text="Choose a Service Booking (Paid, Deposit Paid, or Refunded status).",
        required=False
    )
    sales_booking = forms.ModelChoiceField(
        queryset=SalesBooking.objects.filter(payment_status__in=['deposit_paid', 'refunded']), # Sales only has deposit_paid
        label="Select Sales Booking",
        help_text="Choose a Sales Booking (Deposit Paid or Refunded status).",
        required=False
    )

    class Meta:
        model = RefundRequest
        fields = [
            'hire_booking',
            'service_booking',
            'sales_booking', # Add sales_booking to fields
            'reason',
            'staff_notes',
            'amount_to_refund',
        ]
        widgets = {
            'reason': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Optional: Reason for refund request (e.g., customer cancellation, service issue).'}),
            'staff_notes': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Internal notes regarding the refund processing.'}),
        }
        labels = {
            'reason': "Customer/Admin Reason",
            'amount_to_refund': "Amount to Refund ($)",
        }
        help_texts = {
            'amount_to_refund': "Enter the amount to be refunded. This cannot exceed the amount paid for the booking.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make reason and staff_notes not required by default for admin form
        self.fields['reason'].required = False
        self.fields['staff_notes'].required = False
        self.fields['amount_to_refund'].required = True

        # When editing an existing RefundRequest, set the initial value for the correct booking type
        if self.instance.pk:
            if self.instance.hire_booking:
                self.initial['hire_booking'] = self.instance.hire_booking
            elif self.instance.service_booking:
                self.initial['service_booking'] = self.instance.service_booking
            elif self.instance.sales_booking: # Set initial for sales booking
                self.initial['sales_booking'] = self.instance.sales_booking

    def clean(self):
        """
        Custom validation for the admin refund request form.
        Ensures exactly one of HireBooking, ServiceBooking, or SalesBooking is selected,
        and links the appropriate payment and customer profile.
        Also validates the refund amount against the paid amount.
        """
        cleaned_data = super().clean()
        hire_booking = cleaned_data.get('hire_booking')
        service_booking = cleaned_data.get('service_booking')
        sales_booking = cleaned_data.get('sales_booking') # Get sales_booking
        amount_to_refund = cleaned_data.get('amount_to_refund')

        # Ensure only one booking type is selected
        selected_bookings = [b for b in [hire_booking, service_booking, sales_booking] if b is not None]
        if len(selected_bookings) > 1:
            raise ValidationError("Please select only one type of booking (Hire, Service, or Sales).")
        if not selected_bookings:
            raise ValidationError("Please select a Hire, Service, or Sales Booking.")

        selected_booking = selected_bookings[0]
        max_refund_amount = Decimal('0.00')

        # Link payment and customer profile to the RefundRequest instance based on selected booking type
        # Clear all booking and profile links first for consistency
        self.instance.hire_booking = None
        self.instance.driver_profile = None
        self.instance.service_booking = None
        self.instance.service_profile = None
        self.instance.sales_booking = None
        self.instance.sales_profile = None
        self.instance.payment = None # Clear payment too, will be set below

        if hire_booking:
            if not hire_booking.payment:
                self.add_error('hire_booking', "Selected Hire Booking does not have an associated payment record.")
                return cleaned_data
            self.instance.payment = hire_booking.payment
            self.instance.hire_booking = hire_booking
            self.instance.driver_profile = hire_booking.driver_profile
            max_refund_amount = hire_booking.payment.amount

        elif service_booking:
            if not service_booking.payment:
                self.add_error('service_booking', "Selected Service Booking does not have an associated payment record.")
                return cleaned_data
            self.instance.payment = service_booking.payment
            self.instance.service_booking = service_booking
            self.instance.service_profile = service_booking.service_profile
            max_refund_amount = service_booking.payment.amount
        
        elif sales_booking: # Handle sales booking
            if not sales_booking.payment:
                self.add_error('sales_booking', "Selected Sales Booking does not have an associated payment record.")
                return cleaned_data
            self.instance.payment = sales_booking.payment
            self.instance.sales_booking = sales_booking
            self.instance.sales_profile = sales_booking.sales_profile
            max_refund_amount = sales_booking.payment.amount


        # Validate amount_to_refund against the actual amount paid for the selected booking
        if selected_booking and amount_to_refund is not None:
            if amount_to_refund < 0:
                self.add_error('amount_to_refund', "Amount to refund cannot be a negative value.")
            elif amount_to_refund > max_refund_amount:
                self.add_error('amount_to_refund', f"Amount to refund (${amount_to_refund}) cannot exceed the amount paid for this booking (${max_refund_amount}).")

        return cleaned_data

    def save(self, commit=True):
        """
        Override save to ensure payment, and associated customer profiles
        are correctly linked before saving the RefundRequest instance.
        """
        refund_request = super().save(commit=False)

        # The clean method should have already set these based on the selected booking,
        # but ensure for safety and explicitness.
        # No need for explicit `if refund_request.hire_booking` etc. blocks here
        # as `clean` already sets the correct fields and clears others.

        if commit:
            refund_request.save()
        return refund_request
