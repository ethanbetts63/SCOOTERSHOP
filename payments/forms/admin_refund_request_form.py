# payments/forms/admin_refund_request_form.py

from django import forms
from django.core.exceptions import ValidationError
from payments.models.RefundRequest import RefundRequest
from hire.models import HireBooking
from service.models import ServiceBooking # Import ServiceBooking
from payments.models.PaymentModel import Payment # Assuming Payment is in payments.models.PaymentModel
from service.models import ServiceProfile # Import ServiceProfile

class AdminRefundRequestForm(forms.ModelForm):
    """
    Form for administrators to create or edit a RefundRequest.
    Allows selection of either a HireBooking or a ServiceBooking,
    and input of reason, staff notes, and amount to refund.
    Driver profile/Service profile and payment are automatically linked
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

    class Meta:
        model = RefundRequest
        fields = [
            'hire_booking',
            'service_booking',
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
                # Ensure the other booking type field is disabled if one is set
                self.fields['service_booking'].widget.attrs['disabled'] = 'disabled'
            elif self.instance.service_booking:
                self.initial['service_booking'] = self.instance.service_booking
                # Ensure the other booking type field is disabled if one is set
                self.fields['hire_booking'].widget.attrs['disabled'] = 'disabled'

    def clean(self):
        """
        Custom validation for the admin refund request form.
        Ensures exactly one of either a HireBooking or ServiceBooking is selected,
        and links the appropriate payment, driver_profile, or service_profile.
        Also validates the refund amount against the paid amount.
        """
        cleaned_data = super().clean()
        hire_booking = cleaned_data.get('hire_booking')
        service_booking = cleaned_data.get('service_booking')
        amount_to_refund = cleaned_data.get('amount_to_refund')

        # Ensure only one booking type is selected
        if hire_booking and service_booking:
            raise ValidationError("Please select either a Hire Booking or a Service Booking, not both.")
        if not hire_booking and not service_booking:
            raise ValidationError("Please select either a Hire Booking or a Service Booking.")

        selected_booking = None
        if hire_booking:
            selected_booking = hire_booking
            # Ensure the selected HireBooking has an associated Payment
            if not selected_booking.payment:
                self.add_error('hire_booking', "Selected Hire Booking does not have an associated payment record.")
                # Return early if no payment to prevent further errors related to it
                return cleaned_data

            # Link payment and driver_profile to the RefundRequest instance
            self.instance.payment = selected_booking.payment
            self.instance.driver_profile = selected_booking.driver_profile
            # Clear service_booking and service_profile to ensure data consistency
            self.instance.service_booking = None
            self.instance.service_profile = None

            max_refund_amount = selected_booking.payment.amount

        elif service_booking:
            selected_booking = service_booking
            # Ensure the selected ServiceBooking has an associated Payment
            if not selected_booking.payment:
                self.add_error('service_booking', "Selected Service Booking does not have an associated payment record.")
                # Return early if no payment to prevent further errors related to it
                return cleaned_data
            
            # Link payment and service_profile to the RefundRequest instance
            self.instance.payment = selected_booking.payment
            self.instance.service_profile = selected_booking.service_profile
            # Clear hire_booking and driver_profile to ensure data consistency
            self.instance.hire_booking = None
            self.instance.driver_profile = None

            max_refund_amount = selected_booking.payment.amount

        # Validate amount_to_refund against the actual amount paid for the selected booking
        if selected_booking and amount_to_refund is not None:
            if amount_to_refund < 0:
                self.add_error('amount_to_refund', "Amount to refund cannot be a negative value.")
            elif amount_to_refund > max_refund_amount:
                self.add_error('amount_to_refund', f"Amount to refund (${amount_to_refund}) cannot exceed the amount paid for this booking (${max_refund_amount}).")

        return cleaned_data

    def save(self, commit=True):
        """
        Override save to ensure payment, driver_profile, and service_profile
        are correctly linked before saving the RefundRequest instance.
        """
        refund_request = super().save(commit=False)

        # The clean method should have already set these based on the selected booking,
        # but ensure for safety and explicitness.
        if refund_request.hire_booking:
            if not refund_request.payment:
                refund_request.payment = refund_request.hire_booking.payment
            if not refund_request.driver_profile:
                refund_request.driver_profile = refund_request.hire_booking.driver_profile
            # Ensure service-related fields are cleared
            refund_request.service_booking = None
            refund_request.service_profile = None
        elif refund_request.service_booking:
            if not refund_request.payment:
                refund_request.payment = refund_request.service_booking.payment
            if not refund_request.service_profile:
                refund_request.service_profile = refund_request.service_booking.service_profile
            # Ensure hire-related fields are cleared
            refund_request.hire_booking = None
            refund_request.driver_profile = None

        if commit:
            refund_request.save()
        return refund_request
