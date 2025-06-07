from django.db import transaction
from decimal import Decimal
import uuid # Imported as a general utility, though ServiceBooking's save method handles its reference.

# Assuming these models are in hire/models.py and payments/models.py
from ..models import TempServiceBooking, ServiceBooking, ServiceSettings
from payments.models import Payment

def convert_temp_service_booking(
    temp_booking: TempServiceBooking,
    payment_method: str, # e.g., 'online_full', 'in_store_full'
    booking_payment_status: str, # e.g., 'paid', 'deposit_paid', 'pending'
    amount_paid_on_booking: Decimal,
    calculated_total_on_booking: Decimal, 
    stripe_payment_intent_id: str = None,
    payment_obj: Payment = None, 
) -> ServiceBooking:
    """
    Converts a TempServiceBooking instance into a permanent ServiceBooking instance.

    This function handles:
    1. Creating the permanent ServiceBooking.
    2. Updating the related Payment object (if provided) to link to the new ServiceBooking.
    3. Deleting the temporary booking.
    4. Capturing a snapshot of current refund policy settings and storing it in the Payment object.

    """
    try:
        # Use an atomic transaction to ensure data consistency.
        # If any step fails, the entire transaction is rolled back.
        with transaction.atomic():
            # Retrieve current ServiceSettings to capture refund policy snapshot and currency.
            # This ensures that refund rules applied are those active at the time of booking.
            service_settings = ServiceSettings.objects.first()
            current_refund_settings = {}
            currency_code = 'AUD' # Default currency if ServiceSettings not found

            if service_settings:
                currency_code = service_settings.currency_code
                # Capture all relevant refund policy fields from ServiceSettings.
                current_refund_settings = {
                    'cancel_full_payment_max_refund_days': service_settings.cancel_full_payment_max_refund_days,
                    'cancel_full_payment_max_refund_percentage': float(service_settings.cancel_full_payment_max_refund_percentage),
                    'cancel_full_payment_partial_refund_days': service_settings.cancel_full_payment_partial_refund_days,
                    'cancel_full_payment_partial_refund_percentage': float(service_settings.cancel_full_payment_partial_refund_percentage),
                    'cancel_full_payment_min_refund_days': service_settings.cancel_full_payment_min_refund_days,
                    'cancel_full_payment_min_refund_percentage': float(service_settings.cancel_full_payment_min_refund_percentage),
                    'cancel_deposit_max_refund_days': service_settings.cancel_deposit_max_refund_days,
                    'cancel_deposit_max_refund_percentage': float(service_settings.cancel_deposit_max_refund_percentage),
                    'cancel_deposit_partial_refund_days': service_settings.cancel_deposit_partial_refund_days,
                    'cancel_deposit_partial_refund_percentage': float(service_settings.cancel_deposit_partial_refund_percentage),
                    'cancel_deposit_min_refund_days': service_settings.cancel_deposit_min_refund_days,
                    'cancel_deposit_min_refund_percentage': float(service_settings.cancel_deposit_min_refund_percentage),
                    'refund_deducts_stripe_fee_policy': service_settings.refund_deducts_stripe_fee_policy,
                    'stripe_fee_percentage_domestic': float(service_settings.stripe_fee_percentage_domestic),
                    'stripe_fee_fixed_domestic': float(service_settings.stripe_fee_fixed_domestic),
                    'stripe_fee_percentage_international': float(service_settings.stripe_fee_percentage_international),
                    'stripe_fee_fixed_international': float(service_settings.stripe_fee_fixed_international),
                }

            # Create the permanent ServiceBooking instance.
            # Data is copied from the temporary booking and the function's arguments.
            service_booking = ServiceBooking.objects.create(
                service_type=temp_booking.service_type,
                service_profile=temp_booking.service_profile,
                customer_motorcycle=temp_booking.customer_motorcycle,
                payment_option=temp_booking.payment_option,
                calculated_total=calculated_total_on_booking,
                # Ensure calculated_deposit_amount is a Decimal; default to 0.00 if None.
                calculated_deposit_amount=temp_booking.calculated_deposit_amount if temp_booking.calculated_deposit_amount is not None else Decimal('0.00'),
                amount_paid=amount_paid_on_booking,
                payment_status=booking_payment_status,
                payment_method=payment_method,
                currency=currency_code,
                stripe_payment_intent_id=stripe_payment_intent_id,
                service_date=temp_booking.service_date,
                dropoff_date=temp_booking.dropoff_date,
                dropoff_time=temp_booking.dropoff_time,
                estimated_pickup_date=temp_booking.estimated_pickup_date,
                booking_status='confirmed', # Set initial status to confirmed upon successful conversion.
                customer_notes=temp_booking.customer_notes,
                payment=payment_obj, # Link the ServiceBooking to the Payment object.
            )

            # If a Payment object was provided, update its links and refund snapshot.
            if payment_obj:
                payment_obj.service_booking = service_booking
                # Assuming the Payment model has a 'customer_profile' field to link to the ServiceProfile.
                # Adjust 'customer_profile' to the actual field name in your Payment model.
                payment_obj.customer_profile = service_booking.service_profile
                # If your Payment model has a foreign key to TempServiceBooking, clear it here.
                # This prevents old links from temporary bookings from persisting.
                if hasattr(payment_obj, 'temp_service_booking'):
                    payment_obj.temp_service_booking = None
                payment_obj.refund_policy_snapshot = current_refund_settings
                payment_obj.save()

            # Delete the temporary booking instance after successful conversion.
            temp_booking.delete()

            return service_booking

    except Exception as e:
        # Re-raise the exception to ensure that the atomic transaction is rolled back
        # and to propagate the error for upstream handling (e.g., webhook retry logic).
        raise
