# payments/webhook_handlers.py
from django.db import transaction
import logging

# Import models from hire app
from hire.models import TempHireBooking, HireBooking, BookingAddOn, TempBookingAddOn
# Import Payment model from payments app
from payments.models import Payment
from hire.models import DriverProfile # Import DriverProfile

logger = logging.getLogger(__name__)

def handle_hire_booking_succeeded(payment_obj: Payment, payment_intent_data: dict):
    """
    Handles the business logic for a successful payment_intent.succeeded event
    specifically for a 'hire_booking'.

    This function is responsible for:
    1. Converting the TempHireBooking to a permanent HireBooking.
    2. Copying associated add-ons.
    3. Deleting the temporary booking.
    4. Updating the Payment object to link to the new HireBooking and DriverProfile.
    5. Updating the Payment object's status to reflect the successful payment.

    Args:
        payment_obj (Payment): The Payment model instance linked to this intent.
        payment_intent_data (dict): The data object from the Stripe PaymentIntent event.
    """
    print(f"DEBUG: Entering handle_hire_booking_succeeded for Payment ID: {payment_obj.id}") # Debug print
    logger.info(f"Handling successful hire_booking payment for Payment ID: {payment_obj.id}")
    print(f"DEBUG: Payment Intent Data received: {payment_intent_data}") # Debug print

    try:
        temp_booking = payment_obj.temp_hire_booking

        if temp_booking is None:
            logger.error(f"TempHireBooking not found for Payment ID {payment_obj.id}. Cannot finalize booking.")
            print(f"DEBUG: ERROR - TempHireBooking not found for Payment ID {payment_obj.id}.") # Debug print
            raise TempHireBooking.DoesNotExist(f"TempHireBooking for Payment ID {payment_obj.id} does not exist.")

        print(f"DEBUG: Retrieved TempHireBooking {temp_booking.id} from Payment object.") # Debug print

        # Ensure we are working within an atomic transaction for data consistency
        with transaction.atomic():
            # Determine payment_status for the HireBooking based on the original payment option
            hire_payment_status = 'paid' if temp_booking.payment_option == 'online_full' else 'deposit_paid'
            print(f"DEBUG: Hire payment status determined: {hire_payment_status}") # Debug print

            # Create the HireBooking instance
            hire_booking = HireBooking.objects.create(
                motorcycle=temp_booking.motorcycle,
                driver_profile=temp_booking.driver_profile,
                package=temp_booking.package,
                # UPDATED FIELD: Changed from booked_package_price to total_package_price
                total_package_price=temp_booking.total_package_price, # Total price for the package
                pickup_date=temp_booking.pickup_date,
                pickup_time=temp_booking.pickup_time,
                return_date=temp_booking.return_date,
                return_time=temp_booking.return_time,
                is_international_booking=temp_booking.is_international_booking,
                booked_daily_rate=temp_booking.booked_daily_rate, # Motorcycle's daily rate at booking
                booked_hourly_rate=temp_booking.booked_hourly_rate, # Motorcycle's hourly rate at booking
                total_price=temp_booking.grand_total, # This is the grand total for the entire booking
                deposit_amount=temp_booking.deposit_amount if temp_booking.deposit_amount else 0,
                amount_paid=payment_obj.amount, # Use the amount from the Payment object (actual amount paid)
                payment_status=hire_payment_status,
                payment_method='online',
                currency=temp_booking.currency,
                status='confirmed', # Booking is confirmed upon successful payment
                stripe_payment_intent_id=payment_obj.stripe_payment_intent_id, # Link to Stripe PI
            )
            logger.info(f"Created new HireBooking: {hire_booking.booking_reference} from TempHireBooking {temp_booking.id}")
            print(f"DEBUG: Successfully created HireBooking: {hire_booking.booking_reference}") # Debug print

            # Update the existing Payment object to link to the new HireBooking and DriverProfile
            payment_obj.hire_booking = hire_booking
            payment_obj.driver_profile = hire_booking.driver_profile # Link payment to the driver
            payment_obj.status = payment_intent_data['status'] # Update payment status from Stripe
            # Set temp_hire_booking to None before deleting the temp_booking to ensure SET_NULL works
            payment_obj.temp_hire_booking = None
            payment_obj.save()
            logger.info(f"Updated Payment {payment_obj.id} to link to HireBooking {hire_booking.booking_reference} and DriverProfile {hire_booking.driver_profile.id}.")
            print(f"DEBUG: Updated Payment object with HireBooking and DriverProfile links.") # Debug print


            # Copy add-ons from TempBookingAddOn to BookingAddOn
            temp_booking_addons = TempBookingAddOn.objects.filter(temp_booking=temp_booking)
            print(f"DEBUG: Found {len(temp_booking_addons)} temporary add-ons.") # Debug print
            for temp_addon in temp_booking_addons:
                BookingAddOn.objects.create(
                    booking=hire_booking,
                    addon=temp_addon.addon,
                    quantity=temp_addon.quantity,
                    booked_addon_price=temp_addon.booked_addon_price # Price per unit of the addon at booking
                )
                print(f"DEBUG: Copied add-on: {temp_addon.addon.name} (Qty: {temp_addon.quantity})") # Debug print
            logger.info(f"Copied {len(temp_booking_addons)} add-ons for HireBooking {hire_booking.booking_reference}.")

            # Delete the TempHireBooking and its associated TempBookingAddOns
            # Because TempBookingAddOn has on_delete=CASCADE to TempHireBooking,
            # deleting temp_booking will automatically delete its related TempBookingAddOns.
            temp_booking_id_to_delete = temp_booking.id
            temp_booking.delete()
            logger.info(f"TempHireBooking {temp_booking_id_to_delete} and associated data deleted.")
            print(f"DEBUG: Deleted TempHireBooking {temp_booking_id_to_delete}.") # Debug print

            # At this point, the booking is finalized. You might want to:
            # - Send a confirmation email to the user.
            # - Update inventory (if not already done).
            # - Log the final booking reference for administrative purposes.
            print("DEBUG: Hire booking finalization complete.") # Debug print

    except TempHireBooking.DoesNotExist:
        logger.error(f"TempHireBooking not found for Payment ID {payment_obj.id}. Cannot finalize booking.")
        print(f"DEBUG: ERROR - TempHireBooking not found for Payment ID {payment_obj.id}.") # Debug print
        # Re-raise the exception to ensure the webhook returns a 500, prompting Stripe to retry
        raise
    except Exception as e:
        logger.exception(f"Critical error finalizing hire booking for Payment ID {payment_obj.id}: {e}")
        print(f"DEBUG: CRITICAL ERROR - Exception in handle_hire_booking_succeeded: {e}") # Debug print
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
