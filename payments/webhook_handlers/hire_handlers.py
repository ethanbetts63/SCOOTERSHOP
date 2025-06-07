# payments/webhook_handlers/hire_handlers.py
from django.db import transaction
from decimal import Decimal
from django.conf import settings

# Import models specific to the hire app
from hire.models import TempHireBooking, HireBooking, DriverProfile

# Import Payment model from payments app
from payments.models import Payment

# Import the centralized converter function
from hire.temp_hire_converter import convert_temp_to_hire_booking

# Import the email sending utility
from mailer.utils import send_templated_email


def handle_hire_booking_succeeded(payment_obj: Payment, payment_intent_data: dict):
    """
    Handles the business logic for a successful payment_intent.succeeded event
    specifically for a 'hire_booking'.

    This function is responsible for:
    1. Utilizing the centralized converter to turn TempHireBooking into HireBooking.
    2. Updating the Payment object's status to reflect the successful payment.
    3. Sending confirmation emails to the user and admin.

    Args:
        payment_obj (Payment): The Payment model instance linked to this intent.
        payment_intent_data (dict): The data object from the Stripe PaymentIntent event.
    """
    print(f"DEBUG: Entering handle_hire_booking_succeeded for Payment ID: {payment_obj.id}")

    try:
        temp_booking = payment_obj.temp_hire_booking

        if temp_booking is None:
            print(f"ERROR: TempHireBooking not found for Payment ID {payment_obj.id}. Cannot finalize booking.")
            raise TempHireBooking.DoesNotExist(f"TempHireBooking for Payment ID {payment_obj.id} does not exist.")

        # Determine payment_status for the HireBooking based on the original payment option
        # Correctly map payment_option to hire_payment_status
        if temp_booking.payment_option == 'online_full':
            hire_payment_status = 'paid'
        elif temp_booking.payment_option == 'online_deposit':
            hire_payment_status = 'deposit_paid'
        elif temp_booking.payment_option == 'in_store_full': # Handle in-store payments
            hire_payment_status = 'unpaid' # Or 'in_store_unpaid' if you add that status
        else:
            # Default or error handling for unexpected payment_option
            hire_payment_status = 'unpaid' # Or raise an error
            print(f"WARNING: Unexpected payment_option '{temp_booking.payment_option}' for TempHireBooking {temp_booking.pk}. Defaulting to 'unpaid'.")


        # Use the centralized converter function
        # The converter function already handles the transaction, creation of HireBooking,
        # copying of add-ons, and deletion of TempHireBooking.
        hire_booking = convert_temp_to_hire_booking(
            temp_booking=temp_booking,
            payment_method=temp_booking.payment_option, # Payment method is online for webhook-triggered success
            booking_payment_status=hire_payment_status,
            # Use 'amount_received' from payment_intent_data for the actual amount paid by customer.
            # 'amount' is the requested amount, 'amount_received' is what was actually paid.
            amount_paid_on_booking=Decimal(payment_intent_data['amount_received']) / Decimal('100'),
            stripe_payment_intent_id=payment_obj.stripe_payment_intent_id,
            payment_obj=payment_obj, # Pass the existing payment_obj to be updated by the converter
        )

        # The payment_obj's status is updated by the converter, but we can re-confirm here
        # or add any other post-conversion logic specific to the webhook.
        # For example, ensure the payment_obj status matches the Stripe intent status.
        if payment_obj.status != payment_intent_data['status']:
            payment_obj.status = payment_intent_data['status']
            payment_obj.save()
            print(f"DEBUG: Updated Payment {payment_obj.id} status to {payment_obj.status}.")

        # --- Email Sending for Online Booking Confirmation ---
        # Context for email templates
        email_context = {
            'hire_booking': hire_booking,
            'user': hire_booking.driver_profile.user if hire_booking.driver_profile and hire_booking.driver_profile.user else None,
            'driver_profile': hire_booking.driver_profile,
            'is_in_store': False, # Flag for template logic if needed
        }

        # Send confirmation email to the user
        user_email = hire_booking.driver_profile.user.email if hire_booking.driver_profile.user else hire_booking.driver_profile.email
        if user_email:
            send_templated_email(
                recipient_list=[user_email],
                subject=f"Your Motorcycle Hire Booking Confirmation - {hire_booking.booking_reference}",
                template_name='booking_confirmation_user.html',
                context=email_context,
                user=hire_booking.driver_profile.user if hire_booking.driver_profile and hire_booking.driver_profile.user else None,
                driver_profile=hire_booking.driver_profile,
                booking=hire_booking
            )
            print(f"DEBUG: Sent user booking confirmation email to {user_email}.") # Debug print

        # Send notification email to the admin
        if settings.ADMIN_EMAIL:
            send_templated_email(
                recipient_list=[settings.ADMIN_EMAIL],
                subject=f"New Motorcycle Hire Booking (Online) - {hire_booking.booking_reference}",
                template_name='booking_confirmation_admin.html',
                context=email_context,
                booking=hire_booking
            )
            print(f"DEBUG: Sent admin booking confirmation email.") # Debug print
        # --- End Email Sending ---

    except TempHireBooking.DoesNotExist:
        print(f"ERROR: TempHireBooking not found for Payment ID {payment_obj.id} in handle_hire_booking_succeeded. Cannot finalize booking.")
        # Re-raise the exception to ensure the webhook returns a 500, prompting Stripe to retry
        raise
    except Exception as e:
        print(f"CRITICAL ERROR: Critical error finalizing hire booking for Payment ID {payment_obj.id} in handle_hire_booking_succeeded: {e}")
        # Re-raise the exception to ensure the webhook returns a 500, prompting Stripe to retry
        raise

