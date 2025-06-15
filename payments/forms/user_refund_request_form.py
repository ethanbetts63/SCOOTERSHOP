# payments/forms/user_refund_request_form.py

from django import forms
from django.utils.translation import gettext_lazy as _
import re # Import regex for booking reference parsing

# Assuming these imports based on typical Django app structure
from hire.models import HireBooking, DriverProfile
from service.models import ServiceBooking, ServiceProfile
from inventory.models import SalesBooking, SalesProfile # Import SalesBooking and SalesProfile
from payments.models.RefundRequest import RefundRequest
from payments.models.PaymentModel import Payment


class RefundRequestForm(forms.ModelForm):
    """
    Generalized form for users to request a refund for either a HireBooking,
    ServiceBooking, or SalesBooking.
    Requires booking reference, email, and an optional reason.
    Performs validation to link to the correct booking type, customer profile,
    and payment.
    """
    booking_reference = forms.CharField(
        max_length=50, # Increased max_length to accommodate longer service booking references if needed
        label=_("Booking Reference"),
        help_text=_("Enter your unique booking reference number (e.g., HIRE-XXXXX, SERVICE-XXXXX, or SBK-XXXXX).")
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
        # The actual model instance fields (hire_booking, service_booking, sales_booking,
        # driver_profile, service_profile, sales_profile, payment) will be set in clean().

    def clean(self):
        """
        Custom validation to verify the booking reference and email,
        and to link the RefundRequest to the correct booking (Hire, Service, or Sales),
        customer profile, and Payment.
        """
        cleaned_data = super().clean()
        booking_reference = cleaned_data.get('booking_reference')
        email = cleaned_data.get('email')
        reason = cleaned_data.get('reason')

        booking_object = None
        customer_profile = None
        payment_object = None
        booking_type = None # Will store 'hire', 'service', or 'sales'

        print(f"DEBUG FORM: Cleaning data for booking_reference='{booking_reference}', email='{email}'")

        if booking_reference and email:
            try:
                # 1. Attempt to identify booking type and fetch the booking object
                # Try to match HireBooking first (e.g., starts with "HIRE-")
                if re.match(r'^HIRE-\w+', booking_reference, re.IGNORECASE):
                    print(f"DEBUG FORM: Attempting to match as HireBooking with ref: {booking_reference}")
                    try:
                        booking_object = HireBooking.objects.get(booking_reference__iexact=booking_reference)
                        customer_profile = booking_object.driver_profile
                        payment_object = booking_object.payment
                        booking_type = 'hire'
                        print(f"DEBUG FORM: Successfully found HireBooking: {booking_object.booking_reference}")
                    except HireBooking.DoesNotExist:
                        print(f"DEBUG FORM: HireBooking '{booking_reference}' not found.")
                        pass # Let the general "not found" error handle it later if no other type matches

                # If not a HireBooking, or HireBooking not found, try ServiceBooking (e.g., starts with "SERVICE-" or "SVC-")
                if not booking_object and re.match(r'^(SERVICE|SVC)-\w+', booking_reference, re.IGNORECASE):
                    print(f"DEBUG FORM: Attempting to match as ServiceBooking with ref: {booking_reference}")
                    try:
                        booking_object = ServiceBooking.objects.get(service_booking_reference__iexact=booking_reference)
                        customer_profile = booking_object.service_profile # Assuming ServiceBooking has a 'service_profile' field
                        payment_object = booking_object.payment
                        booking_type = 'service'
                        print(f"DEBUG FORM: Successfully found ServiceBooking: {booking_object.service_booking_reference}")
                    except ServiceBooking.DoesNotExist:
                        print(f"DEBUG FORM: ServiceBooking '{booking_reference}' not found.")
                        pass # Let the general "not found" error handle it
                
                # If no booking of either type, try SalesBooking (e.g., starts with "SBK-")
                if not booking_object and re.match(r'^SBK-\w+', booking_reference, re.IGNORECASE):
                    print(f"DEBUG FORM: Attempting to match as SalesBooking with ref: {booking_reference}")
                    try:
                        booking_object = SalesBooking.objects.get(sales_booking_reference__iexact=booking_reference)
                        customer_profile = booking_object.sales_profile # Assuming SalesBooking has a 'sales_profile' field
                        payment_object = booking_object.payment
                        booking_type = 'sales'
                        print(f"DEBUG FORM: Successfully found SalesBooking: {booking_object.sales_booking_reference}")
                    except SalesBooking.DoesNotExist:
                        print(f"DEBUG FORM: SalesBooking '{booking_reference}' not found.")
                        pass # Let the general "not found" error handle it

                # If no booking of any type was found
                if not booking_object:
                    print(f"DEBUG FORM: No booking object found for '{booking_reference}'. Adding error.")
                    self.add_error('booking_reference', _("No booking found with this reference number."))
                    return cleaned_data

                # 2. Validate the email matches the customer profile's email
                print(f"DEBUG FORM: Validating email. Customer email: '{customer_profile.email.lower()}', Provided email: '{email.lower()}'")
                if not customer_profile or customer_profile.email.lower() != email.lower():
                    print(f"DEBUG FORM: Email mismatch for booking '{booking_reference}'. Adding error.")
                    self.add_error('email', _("The email address does not match the one registered for this booking."))
                    return cleaned_data

                # 3. Check if a payment exists for this booking
                print(f"DEBUG FORM: Checking for payment object for booking: {booking_object}")
                if not payment_object:
                    print(f"DEBUG FORM: No payment object found for booking '{booking_reference}'. Adding error.")
                    self.add_error('booking_reference', _("No payment record found for this booking."))
                    return cleaned_data
                print(f"DEBUG FORM: Payment object found: {payment_object.id}, status: {payment_object.status}")

                # 4. Check payment status for eligibility (must be 'succeeded' for refund)
                if payment_object.status != 'succeeded':
                     print(f"DEBUG FORM: Payment status is '{payment_object.status}', not 'succeeded'. Adding error.")
                     self.add_error('booking_reference', _("This booking's payment is not in a 'succeeded' status and is not eligible for a refund."))
                     return cleaned_data
                print(f"DEBUG FORM: Payment status is 'succeeded'.")

                # 5. Check if a refund request for this booking/payment is already in progress
                existing_refund_requests = RefundRequest.objects.filter(
                    payment=payment_object,
                    status__in=['unverified', 'pending', 'approved', 'reviewed_pending_approval']
                )
                if existing_refund_requests.exists():
                    print(f"DEBUG FORM: Existing refund request found for payment {payment_object.id}. Adding error.")
                    self.add_error(None, _("A refund request for this booking is already in progress."))
                    return cleaned_data
                print("DEBUG FORM: No existing refund request in progress.")

                # If all validations pass, set the instance's related objects
                self.instance.payment = payment_object
                self.instance.status = 'unverified' # Initial status upon user submission
                self.instance.is_admin_initiated = False # User initiated
                self.instance.reason = reason # Set the reason
                self.instance.request_email = email.lower() # Store the email provided by the user in lowercase
                print(f"DEBUG FORM: Instance attributes set: payment={payment_object.id}, status='unverified', email='{email.lower()}'")

                # Clear all booking and profile fields first to ensure only the relevant one is set
                self.instance.hire_booking = None
                self.instance.driver_profile = None
                self.instance.service_booking = None
                self.instance.service_profile = None
                self.instance.sales_booking = None
                self.instance.sales_profile = None

                # Set the specific booking and profile fields based on the identified type
                if booking_type == 'hire':
                    self.instance.hire_booking = booking_object
                    self.instance.driver_profile = customer_profile
                    print(f"DEBUG FORM: Set hire_booking and driver_profile for instance.")
                elif booking_type == 'service':
                    self.instance.service_booking = booking_object
                    self.instance.service_profile = customer_profile
                    print(f"DEBUG FORM: Set service_booking and service_profile for instance.")
                elif booking_type == 'sales':
                    self.instance.sales_booking = booking_object
                    self.instance.sales_profile = customer_profile
                    print(f"DEBUG FORM: Set sales_booking and sales_profile for instance.")

            except DriverProfile.DoesNotExist:
                print("DEBUG FORM: DriverProfile.DoesNotExist caught.")
                self.add_error(None, _("Associated driver profile not found for this hire booking."))
            except ServiceProfile.DoesNotExist:
                print("DEBUG FORM: ServiceProfile.DoesNotExist caught.")
                self.add_error(None, _("Associated service profile not found for this service booking."))
            except SalesProfile.DoesNotExist: # Added SalesProfile DoesNotExist
                print("DEBUG FORM: SalesProfile.DoesNotExist caught.")
                self.add_error(None, _("Associated sales profile not found for this sales booking."))
            except Exception as e:
                # Catch any other unexpected errors during lookup or processing
                print(f"DEBUG FORM: General Exception caught: {e}")
                self.add_error(None, _(f"An unexpected error occurred: {e}. Please try again or contact support."))
        else:
            print("DEBUG FORM: Booking reference or email is missing. Not proceeding with detailed validation.")

        return cleaned_data

    def save(self, commit=True):
        """
        Override save to ensure related objects (hire_booking, service_booking, sales_booking,
        driver_profile, service_profile, sales_profile, payment) are set before saving.
        """
        print("DEBUG FORM: Calling custom save method.")
        refund_request = super().save(commit=False)
        # The clean method should have already set these instance attributes
        if commit:
            print("DEBUG FORM: Committing save.")
            refund_request.save()
        print("DEBUG FORM: Custom save method completed.")
        return refund_request
