# payments/forms/user_refund_request_form.py

from django import forms
from django.utils.translation import gettext_lazy as _
import re # Import regex for booking reference parsing

# Assuming these imports based on typical Django app structure
from hire.models import HireBooking, DriverProfile
from service.models import ServiceBooking, ServiceProfile
from payments.models.RefundRequest import RefundRequest
from payments.models.PaymentModel import Payment


class RefundRequestForm(forms.ModelForm):
    """
    Generalized form for users to request a refund for either a HireBooking
    or a ServiceBooking.
    Requires booking reference, email, and an optional reason.
    Performs validation to link to the correct booking type, customer profile,
    and payment.
    """
    booking_reference = forms.CharField(
        max_length=50, # Increased max_length to accommodate longer service booking references if needed
        label=_("Booking Reference"),
        help_text=_("Enter your unique booking reference number (e.g., HIRE-XXXXX or SERVICE-XXXXX).")
    )
    email = forms.EmailField(
        label=_("Your Email Address"),
        help_text=_("Enter the email address used for this booking.")
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'placeholder': _('Optional: Briefly explain why you are requesting a refund.')}),
        required=False,
        label=_("Reason for Refund")
    )

    class Meta:
        model = RefundRequest
        fields = ['booking_reference', 'email', 'reason'] # These are the only fields the user inputs directly

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # No direct linking of form fields to model fields here for initial setup.
        # The actual model instance fields (hire_booking, service_booking,
        # driver_profile, service_profile, payment) will be set in clean().

    def clean(self):
        """
        Custom validation to verify the booking reference and email,
        and to link the RefundRequest to the correct booking (Hire or Service),
        customer profile, and Payment.
        """
        cleaned_data = super().clean()
        booking_reference = cleaned_data.get('booking_reference')
        email = cleaned_data.get('email')
        reason = cleaned_data.get('reason')

        booking_object = None
        customer_profile = None
        payment_object = None
        booking_type = None # Will store 'hire' or 'service'

        if booking_reference and email:
            try:
                # 1. Attempt to identify booking type and fetch the booking object
                # Try to match HireBooking first (e.g., starts with "HIRE-")
                if re.match(r'^HIRE-\w+', booking_reference, re.IGNORECASE):
                    try:
                        booking_object = HireBooking.objects.get(booking_reference__iexact=booking_reference)
                        customer_profile = booking_object.driver_profile
                        # Assuming a OneToOneField from HireBooking to Payment named 'payment'
                        payment_object = booking_object.payment
                        booking_type = 'hire'
                    except HireBooking.DoesNotExist:
                        # If not found as HireBooking, don't raise error immediately,
                        # try ServiceBooking next if a specific pattern suggests it.
                        pass # Let the general "not found" error handle it later if no other type matches

                # If not a HireBooking, or HireBooking not found, try ServiceBooking (e.g., starts with "SERVICE-")
                if not booking_object and re.match(r'^SERVICE-\w+', booking_reference, re.IGNORECASE):
                    try:
                        booking_object = ServiceBooking.objects.get(service_booking_reference__iexact=booking_reference)
                        customer_profile = booking_object.service_profile # Assuming ServiceBooking has a 'service_profile' field
                        # Assuming a OneToOneField from ServiceBooking to Payment named 'payment_for_service'
                        payment_object = booking_object.payment_for_service
                        booking_type = 'service'
                    except ServiceBooking.DoesNotExist:
                        pass # Let the general "not found" error handle it

                # If no booking of either type was found
                if not booking_object:
                    self.add_error('booking_reference', _("No booking found with this reference number."))
                    return cleaned_data

                # 2. Validate the email matches the customer profile's email
                if not customer_profile or customer_profile.email.lower() != email.lower():
                    self.add_error('email', _("The email address does not match the one registered for this booking."))
                    return cleaned_data

                # 3. Check if a payment exists for this booking
                if not payment_object:
                    self.add_error('booking_reference', _("No payment record found for this booking."))
                    return cleaned_data

                # 4. Check payment status for eligibility (must be 'succeeded' for refund)
                if payment_object.status != 'succeeded':
                     self.add_error('booking_reference', _("This booking's payment is not in a 'succeeded' status and is not eligible for a refund."))
                     return cleaned_data

                # 5. Check if a refund request for this booking/payment is already in progress
                existing_refund_requests = RefundRequest.objects.filter(
                    payment=payment_object,
                    status__in=['unverified', 'pending', 'approved', 'reviewed_pending_approval']
                )
                if existing_refund_requests.exists():
                    self.add_error(None, _("A refund request for this booking is already in progress."))
                    return cleaned_data

                # If all validations pass, set the instance's related objects
                self.instance.payment = payment_object
                self.instance.status = 'unverified' # Initial status upon user submission
                self.instance.is_admin_initiated = False # User initiated
                self.instance.reason = reason # Set the reason
                self.instance.request_email = email.lower() # Store the email provided by the user in lowercase

                # Set the specific booking and profile fields based on the identified type
                if booking_type == 'hire':
                    self.instance.hire_booking = booking_object
                    self.instance.driver_profile = customer_profile
                    # Ensure the service-related fields are cleared for hire bookings
                    self.instance.service_booking = None
                    self.instance.service_profile = None
                elif booking_type == 'service':
                    self.instance.service_booking = booking_object
                    self.instance.service_profile = customer_profile
                    # Ensure the hire-related fields are cleared for service bookings
                    self.instance.hire_booking = None
                    self.instance.driver_profile = None

            except DriverProfile.DoesNotExist:
                self.add_error(None, _("Associated driver profile not found for this hire booking."))
            except ServiceProfile.DoesNotExist:
                self.add_error(None, _("Associated service profile not found for this service booking."))
            except Exception as e:
                # Catch any other unexpected errors during lookup or processing
                self.add_error(None, _(f"An unexpected error occurred: {e}. Please try again or contact support."))

        return cleaned_data

    def save(self, commit=True):
        """
        Override save to ensure related objects (hire_booking, service_booking,
        driver_profile, service_profile, payment) are set before saving.
        """
        refund_request = super().save(commit=False)
        # The clean method should have already set these instance attributes
        if commit:
            refund_request.save()
        return refund_request

