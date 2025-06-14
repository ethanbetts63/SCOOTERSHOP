from django.db import transaction
import logging
from decimal import Decimal

from .models import TempHireBooking, HireBooking, BookingAddOn, TempBookingAddOn
from payments.models import Payment
from dashboard.models import HireSettings

logger = logging.getLogger(__name__)

def convert_temp_to_hire_booking(
    temp_booking: TempHireBooking,
    payment_method: str,
    booking_payment_status: str,
    amount_paid_on_booking: Decimal,
    stripe_payment_intent_id: str = None,
    payment_obj: Payment = None,
) -> HireBooking:
    """
    Converts a TempHireBooking instance into a permanent HireBooking instance.

    This function handles:
    1. Creating the permanent HireBooking.
    2. Copying associated add-ons.
    3. Updating the related Payment object (if provided) to link to the new HireBooking.
    4. Deleting the temporary booking and its add-ons.
    5. Capturing a snapshot of current refund policy settings and storing it in the Payment object.

    Args:
        temp_booking (TempHireBooking): The temporary booking instance to convert.
        payment_method (str): The method of payment for the final HireBooking
                              (e.g., 'online', 'in_store').
        booking_payment_status (str): The payment status for the final HireBooking
                                      (e.g., 'paid', 'deposit_paid', 'pending_in_store').
        amount_paid_on_booking (Decimal): The actual amount paid for this booking.
        stripe_payment_intent_id (str, optional): The Stripe Payment Intent ID, if applicable.
                                                  Defaults to None.
        payment_obj (Payment, optional): The Payment model instance linked to this booking.
                                        If provided, it will be updated. Defaults to None.

    Returns:
        HireBooking: The newly created permanent HireBooking instance.

    Raises:
        Exception: If any error occurs during the conversion process.
    """
    logger.info(f"Attempting to convert TempHireBooking {temp_booking.id} to HireBooking.")

    try:
        with transaction.atomic():
            hire_settings = HireSettings.objects.first()
            current_refund_settings = {}
            if hire_settings:
                current_refund_settings = {
                    'cancellation_upfront_full_refund_days': hire_settings.cancellation_upfront_full_refund_days,
                    'cancellation_upfront_partial_refund_days': hire_settings.cancellation_upfront_partial_refund_days,
                    'cancellation_upfront_partial_refund_percentage': float(hire_settings.cancellation_upfront_partial_refund_percentage),
                    'cancellation_upfront_minimal_refund_days': hire_settings.cancellation_upfront_minimal_refund_days,
                    'cancellation_upfront_minimal_refund_percentage': float(hire_settings.cancellation_upfront_minimal_refund_percentage),
                    'cancellation_deposit_full_refund_days': hire_settings.cancellation_deposit_full_refund_days,
                    'cancellation_deposit_partial_refund_days': hire_settings.cancellation_deposit_partial_refund_days,
                    'cancellation_deposit_partial_refund_percentage': float(hire_settings.cancellation_deposit_partial_refund_percentage),
                    'cancellation_deposit_minimal_refund_days': hire_settings.cancellation_deposit_minimal_refund_days,
                    'cancellation_deposit_minimal_refund_percentage': float(hire_settings.cancellation_deposit_minimal_refund_percentage),
                    'deposit_enabled': hire_settings.deposit_enabled,
                    'default_deposit_calculation_method': hire_settings.default_deposit_calculation_method,
                    'deposit_percentage': float(hire_settings.deposit_percentage),
                    'deposit_amount': float(hire_settings.deposit_amount),
                }
            else:
                pass
            
            hire_booking = HireBooking.objects.create(
                motorcycle=temp_booking.motorcycle,
                driver_profile=temp_booking.driver_profile,
                package=temp_booking.package,
                total_hire_price=temp_booking.total_hire_price,
                total_addons_price=temp_booking.total_addons_price,
                total_package_price=temp_booking.total_package_price,
                grand_total=temp_booking.grand_total,
                pickup_date=temp_booking.pickup_date,
                pickup_time=temp_booking.pickup_time,
                return_date=temp_booking.return_date,
                return_time=temp_booking.return_time,
                is_international_booking=temp_booking.is_international_booking,
                booked_daily_rate=temp_booking.booked_daily_rate,
                booked_hourly_rate=temp_booking.booked_hourly_rate,
                deposit_amount=temp_booking.deposit_amount if temp_booking.deposit_amount is not None else Decimal('0.00'),
                amount_paid=amount_paid_on_booking,
                payment_status=booking_payment_status,
                payment_method=payment_method,
                currency=temp_booking.currency,
                status='confirmed',
                stripe_payment_intent_id=stripe_payment_intent_id,
                payment=payment_obj,
            )
            if payment_obj:
                payment_obj.hire_booking = hire_booking
                payment_obj.driver_profile = hire_booking.driver_profile
                payment_obj.temp_hire_booking = None
                payment_obj.refund_policy_snapshot = current_refund_settings
                payment_obj.save()

            temp_booking_addons = TempBookingAddOn.objects.filter(temp_booking=temp_booking)
            for temp_addon in temp_booking_addons:
                BookingAddOn.objects.create(
                    booking=hire_booking,
                    addon=temp_addon.addon,
                    quantity=temp_addon.quantity,
                    booked_addon_price=temp_addon.booked_addon_price
                )
            logger.info(f"Copied {len(temp_booking_addons)} add-ons for HireBooking {hire_booking.booking_reference}.")

            temp_booking_id_to_delete = temp_booking.id
            temp_booking.delete()
            logger.info(f"TempHireBooking {temp_booking_id_to_delete} and associated data deleted.")

            return hire_booking

    except Exception as e:
        logger.exception(f"Error converting TempHireBooking {temp_booking.id} to HireBooking: {e}")
        raise