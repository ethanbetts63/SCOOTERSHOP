# payments/webhook_handlers.py
from django.db import transaction
import logging
from decimal import Decimal

# Import models from hire app
from hire.models import TempHireBooking, HireBooking, BookingAddOn, TempBookingAddOn
# Import Payment model from payments app
from payments.models import Payment
from hire.models import DriverProfile # Import DriverProfile

# Import the new converter function
from hire.temp_hire_converter import convert_temp_to_hire_booking

logger = logging.getLogger(__name__)

def handle_hire_booking_succeeded(payment_obj: Payment, payment_intent_data: dict):
    """
    Handles the business logic for a successful payment_intent.succeeded event
    specifically for a 'hire_booking'.

    This function is responsible for:
    1. Utilizing the centralized converter to turn TempHireBooking into HireBooking.
    2. Updating the Payment object's status to reflect the successful payment.

    Args:
        payment_obj (Payment): The Payment model instance linked to this intent.
        payment_intent_data (dict): The data object from the Stripe PaymentIntent event.
    """
    logger.info(f"Handling successful hire_booking payment for Payment ID: {payment_obj.id}")

    try:
        temp_booking = payment_obj.temp_hire_booking

        if temp_booking is None:
            logger.error(f"TempHireBooking not found for Payment ID {payment_obj.id}. Cannot finalize booking.")
            raise TempHireBooking.DoesNotExist(f"TempHireBooking for Payment ID {payment_obj.id} does not exist.")

        # Determine payment_status for the HireBooking based on the original payment option
        hire_payment_status = 'paid' if temp_booking.payment_option == 'online_full' else 'deposit_paid'

        # Use the centralized converter function
        # The converter function already handles the transaction, creation of HireBooking,
        # copying of add-ons, and deletion of TempHireBooking.
        hire_booking = convert_temp_to_hire_booking(
            temp_booking=temp_booking,
            payment_method='online', # Payment method is online for webhook-triggered success
            booking_payment_status=hire_payment_status,
            # CHANGE: Use 'amount' key from payment_intent_data, as 'amount_received' is causing KeyError.
            # Stripe's PaymentIntent object typically uses 'amount' for the total amount.
            amount_paid_on_booking=Decimal(payment_intent_data['amount']) / Decimal('100'), # Amount received from Stripe
            stripe_payment_intent_id=payment_obj.stripe_payment_intent_id,
            payment_obj=payment_obj, # Pass the existing payment_obj to be updated by the converter
        )

        # The payment_obj's status is updated by the converter, but we can re-confirm here
        # or add any other post-conversion logic specific to the webhook.
        # For example, ensure the payment_obj status matches the Stripe intent status.
        if payment_obj.status != payment_intent_data['status']:
            payment_obj.status = payment_intent_data['status']
            payment_obj.save()
            logger.info(f"Updated Payment {payment_obj.id} status to {payment_obj.status}.")

        # At this point, the booking is finalized. You might want to:
        # - Send a confirmation email to the user.
        # - Update inventory (if not already done).
        # - Log the final booking reference for administrative purposes.

    except TempHireBooking.DoesNotExist:
        logger.error(f"TempHireBooking not found for Payment ID {payment_obj.id}. Cannot finalize booking.")
        # Re-raise the exception to ensure the webhook returns a 500, prompting Stripe to retry
        raise
    except Exception as e:
        logger.exception(f"Critical error finalizing hire booking for Payment ID {payment_obj.id}: {e}")
        # Re-raise the exception to ensure the webhook returns a 500, prompting Stripe to retry
        raise

# You can define a dictionary to map booking_type to handler functions
WEBHOOK_HANDLERS = {
    'hire_booking': {
        'payment_intent.succeeded': handle_hire_booking_succeeded,
        # Add other event types for hire_booking if needed, e.g., 'payment_intent.payment_failed': handle_hire_booking_failed
    },
    # 'service_booking': {
    #     'payment_intent.succeeded': handle_service_booking_succeeded,
    # },
    # Add more booking types and their handlers here
}
