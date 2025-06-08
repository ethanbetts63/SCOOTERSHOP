# payments/forms/user_hire_refund_request_form.py

from django import forms
from hire.models import HireBooking # Assuming HireBooking is in hire.models
from hire.models import DriverProfile # Assuming DriverProfile is in hire.models
from payments.models.RefundRequest import HireRefundRequest
from payments.models.PaymentModel import Payment # Assuming Payment is in payments.models.PaymentModel

class UserHireRefundRequestForm(forms.ModelForm):
    """
    Form for users to request a refund for a booking.
    Requires booking reference, email, and an optional reason.
    Performs validation to link to the correct HireBooking and DriverProfile.
    """
    booking_reference = forms.CharField(
        max_length=20,
        label="Booking Reference",
        help_text="Enter your unique booking reference number (e.g., HIRE-CC2FA826)."
    )
    email = forms.EmailField(
        label="Your Email Address",
        help_text="Enter the email address used for this booking."
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'placeholder': 'Optional: Briefly explain why you are requesting a refund.'}),
        required=False,
        label="Reason for Refund"
    )

    class Meta:
        model = HireRefundRequest
        fields = ['booking_reference', 'email', 'reason'] # These are the only fields the user inputs directly

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure the form's fields are not linked to model fields directly for initial setup
        # The actual model instance fields (hire_booking, driver_profile, payment) will be set in clean()

    def clean(self):
        """
        Custom validation to verify the booking reference and email,
        and to link the RefundRequest to the correct HireBooking, DriverProfile, and Payment.
        """
        cleaned_data = super().clean()
        booking_reference = cleaned_data.get('booking_reference')
        email = cleaned_data.get('email')
        reason = cleaned_data.get('reason')

        hire_booking = None
        driver_profile = None
        payment = None

        if booking_reference and email:
            try:
                # 1. Find the HireBooking by booking_reference
                hire_booking = HireBooking.objects.get(booking_reference__iexact=booking_reference)

                # 2. Get the associated DriverProfile
                driver_profile = hire_booking.driver_profile

                # 3. Verify the email matches the DriverProfile's email
                if driver_profile.email.lower() != email.lower():
                    self.add_error('email', "The email address does not match the one registered for this booking.")
                    return cleaned_data # Return early if email doesn't match

                # 4. Check if a payment exists for this booking and if it's eligible for refund
                # Only allow refunds for 'paid' or 'deposit_paid' bookings
                if hire_booking.payment_status not in ['paid', 'deposit_paid']:
                    self.add_error('booking_reference', "This booking is not eligible for a refund (e.g., not paid or already cancelled).")
                    return cleaned_data

                # 5. Get the associated Payment instance
                # Assuming HireBooking has a OneToOneField to Payment named 'payment'
                payment = hire_booking.payment
                if not payment:
                    self.add_error('booking_reference', "No payment record found for this booking.")
                    return cleaned_data

                # Check if a refund request for this booking/payment is already in 'pending' or 'approved' status
                # This prevents duplicate active refund requests
                existing_refund_requests = HireRefundRequest.objects.filter(
                    hire_booking=hire_booking,
                    payment=payment,
                    status__in=['unverified', 'pending', 'approved']
                )
                if existing_refund_requests.exists():
                    # Add non-field error
                    self.add_error(None, "A refund request for this booking is already in progress.")
                    return cleaned_data

            except HireBooking.DoesNotExist:
                self.add_error('booking_reference', "No booking found with this reference number.")
            except DriverProfile.DoesNotExist:
                # This case should ideally not happen if HireBooking always has a driver_profile
                self.add_error(None, "Associated driver profile not found for this booking.")
            except Exception as e:
                # Catch any other unexpected errors during lookup
                self.add_error(None, f"An unexpected error occurred: {e}. Please try again or contact support.")

        # If validation passes, set the instance's related objects
        if hire_booking and driver_profile and payment:
            self.instance.hire_booking = hire_booking
            self.instance.driver_profile = driver_profile
            self.instance.payment = payment
            self.instance.status = 'unverified' # Set default status
            self.instance.is_admin_initiated = False # User initiated
            self.instance.reason = reason # Set the reason
            self.instance.request_email = email.lower() # Store the email provided by the user in lowercase

        return cleaned_data

    def save(self, commit=True):
        """
        Override save to ensure related objects are set before saving.
        """
        refund_request = super().save(commit=False)
        # The clean method should have already set these
        if commit:
            refund_request.save()
        return refund_request
