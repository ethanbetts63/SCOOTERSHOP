# payments/forms/admin_hire_refund_request_form.py

from django import forms
from payments.models.RefundRequest import RefundRequest
from hire.models import HireBooking # Assuming HireBooking is in hire.models
from payments.models.PaymentModel import Payment # Assuming Payment is in payments.models.PaymentModel

class AdminRefundRequestForm(forms.ModelForm):
    """
    Form for administrators to create or edit a RefundRequest.
    Allows selection of a HireBooking, and input of reason, staff notes, and amount to refund.
    Driver profile and payment are automatically linked from the selected HireBooking.
    """
    # Override the hire_booking field to use a ModelChoiceField for selection
    hire_booking = forms.ModelChoiceField(
        queryset=HireBooking.objects.filter(payment_status__in=['paid', 'deposit_paid']),
        label="Select Hire Booking",
        help_text="Choose the booking for which the refund is being requested. Only bookings with 'Paid' or 'Deposit Paid' status are shown."
    )

    class Meta:
        model = RefundRequest
        fields = [
            'hire_booking',
            'reason',
            'staff_notes',
            'amount_to_refund',
            # 'is_admin_initiated', # Removed from fields as it will be set automatically by the view
        ]
        widgets = {
            'reason': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Optional: Reason for refund request (e.g., customer cancellation, service issue).'}),
            'staff_notes': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Internal notes regarding the refund processing.'}),
        }
        labels = {
            'reason': "Customer/Admin Reason",
            'amount_to_refund': "Amount to Refund ($)",
            # 'is_admin_initiated': "Admin Initiated?", # Label no longer needed if field is removed
        }
        help_texts = {
            'amount_to_refund': "Enter the amount to be refunded. This cannot exceed the amount paid for the booking.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['reason'].required = False
        self.fields['staff_notes'].required = False
        self.fields['amount_to_refund'].required = True

        # No need to set initial['is_admin_initiated'] here, as it will be set by the view.

    def clean(self):
        """
        Custom validation for the admin refund request form.
        Ensures the selected booking has a payment and driver profile,
        and that the refund amount does not exceed the paid amount.
        """
        cleaned_data = super().clean()
        hire_booking = cleaned_data.get('hire_booking')
        amount_to_refund = cleaned_data.get('amount_to_refund')

        if hire_booking:
            # Ensure the selected HireBooking has an associated Payment
            if not hire_booking.payment:
                self.add_error('hire_booking', "Selected booking does not have an associated payment record.")
                return cleaned_data # Return early if no payment

            # Set the payment and driver_profile on the RefundRequest instance
            # These fields are not directly in the form, but are set during clean
            # to be saved with the RefundRequest instance.
            self.instance.payment = hire_booking.payment
            self.instance.driver_profile = hire_booking.driver_profile

            # Validate amount_to_refund against the actual amount paid for the booking
            if amount_to_refund is not None:
                # Changed from <= 0 to < 0 to allow 0 as a valid refund amount.
                if amount_to_refund < 0:
                    self.add_error('amount_to_refund', "Amount to refund cannot be a negative value.")
                elif amount_to_refund > hire_booking.payment.amount:
                    self.add_error('amount_to_refund', f"Amount to refund (${amount_to_refund}) cannot exceed the amount paid for this booking (${hire_booking.payment.amount}).")

        return cleaned_data

    def save(self, commit=True):
        """
        Override save to ensure payment and driver_profile are set before saving.
        """
        refund_request = super().save(commit=False)
        # The clean method should have already set these, but ensure for safety
        if refund_request.hire_booking and not refund_request.payment:
            refund_request.payment = refund_request.hire_booking.payment
        if refund_request.hire_booking and not refund_request.driver_profile:
            refund_request.driver_profile = refund_request.hire_booking.driver_profile

        if commit:
            refund_request.save()
        return refund_request
