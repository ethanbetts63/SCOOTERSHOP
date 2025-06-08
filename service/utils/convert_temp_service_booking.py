from django.db import transaction
from decimal import Decimal
import uuid

from ..models import TempServiceBooking, ServiceBooking, ServiceSettings
from payments.models import Payment

def convert_temp_service_booking(
    temp_booking: TempServiceBooking,
    payment_method: str,
    booking_payment_status: str,
    amount_paid_on_booking: Decimal,
    calculated_total_on_booking: Decimal, 
    stripe_payment_intent_id: str = None,
    payment_obj: Payment = None, 
) -> ServiceBooking:
    try:
        with transaction.atomic():
            service_settings = ServiceSettings.objects.first()
            current_refund_settings = {}
            currency_code = 'AUD'

            if service_settings:
                currency_code = service_settings.currency_code
                current_refund_settings = {
                    'currency_code': currency_code, 
                    'cancel_full_payment_max_refund_days': service_settings.cancel_full_payment_max_refund_days,
                    'cancel_full_payment_max_refund_percentage': float(service_settings.cancel_full_payment_max_refund_percentage),
                    'cancel_full_payment_partial_refund_days': service_settings.cancel_full_payment_partial_refund_days,
                    'cancel_full_payment_partial_refund_percentage': float(service_settings.cancel_full_payment_partial_refund_percentage),
                    'cancel_full_payment_min_refund_days': service_settings.cancel_full_payment_min_refund_days,
                    'cancel_full_payment_min_refund_percentage': float(service_settings.cancel_full_payment_min_refund_percentage),
                    'cancellation_deposit_full_refund_days': service_settings.cancellation_deposit_full_refund_days,
                    'cancel_deposit_max_refund_percentage': float(service_settings.cancel_deposit_max_refund_percentage),
                    'cancellation_deposit_partial_refund_days': service_settings.cancellation_deposit_partial_refund_days,
                    'cancellation_deposit_partial_refund_percentage': float(service_settings.cancellation_deposit_partial_refund_percentage),
                    'cancellation_deposit_minimal_refund_days': service_settings.cancellation_deposit_minimal_refund_days,
                    'cancellation_deposit_minimal_refund_percentage': float(service_settings.cancellation_deposit_minimal_refund_percentage),
                    'refund_deducts_stripe_fee_policy': service_settings.refund_deducts_stripe_fee_policy,
                    'stripe_fee_percentage_domestic': float(service_settings.stripe_fee_percentage_domestic),
                    'stripe_fee_fixed_domestic': float(service_settings.stripe_fee_fixed_domestic),
                    'stripe_fee_percentage_international': float(service_settings.stripe_fee_percentage_international),
                    'stripe_fee_fixed_international': float(service_settings.stripe_fee_fixed_international),
                }

            service_booking = ServiceBooking.objects.create(
                service_type=temp_booking.service_type,
                service_profile=temp_booking.service_profile,
                customer_motorcycle=temp_booking.customer_motorcycle,
                payment_option=temp_booking.payment_option,
                calculated_total=calculated_total_on_booking,
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
                booking_status='confirmed',
                customer_notes=temp_booking.customer_notes,
                payment=payment_obj,
            )

            if payment_obj:
                payment_obj.service_booking = service_booking
                # Updated to use the new 'service_customer_profile' field
                payment_obj.service_customer_profile = service_booking.service_profile
                if hasattr(payment_obj, 'temp_service_booking'):
                    payment_obj.temp_service_booking = None
                payment_obj.refund_policy_snapshot = current_refund_settings
                payment_obj.save()

            temp_booking.delete()

            return service_booking

    except Exception as e:
        raise
