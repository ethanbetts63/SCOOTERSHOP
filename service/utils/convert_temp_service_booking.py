from django.db import transaction
from decimal import Decimal
from service.utils.send_booking_to_mechanicdesk import send_booking_to_mechanicdesk
from service.models import ServiceBooking, ServiceSettings
from payments.models import RefundPolicySettings

def convert_temp_service_booking(
    temp_booking,
    payment_method,
    booking_payment_status,
    amount_paid_on_booking,
    calculated_total_on_booking,
    stripe_payment_intent_id = None,
    payment_obj = None,
):
    try:
        with transaction.atomic():
            service_settings = ServiceSettings.objects.first()

            currency_code = 'AUD'
            if service_settings:
                currency_code = service_settings.currency_code

            service_booking = ServiceBooking.objects.create(
                service_type=temp_booking.service_type,
                service_profile=temp_booking.service_profile,
                customer_motorcycle=temp_booking.customer_motorcycle,
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
                payment_obj.amount = amount_paid_on_booking

                payment_obj.currency = currency_code
                payment_obj.status = booking_payment_status
                payment_obj.stripe_payment_intent_id = stripe_payment_intent_id
                payment_obj.service_booking = service_booking
                payment_obj.service_customer_profile = service_booking.service_profile

                if hasattr(payment_obj, 'temp_service_booking') and payment_obj.temp_service_booking:
                    payment_obj.temp_service_booking = None

                try:
                    refund_settings = RefundPolicySettings.objects.first()
                    if refund_settings:
                        payment_obj.refund_policy_snapshot = {
                            'cancellation_full_payment_full_refund_days': refund_settings.cancellation_full_payment_full_refund_days,
                            'cancellation_full_payment_partial_refund_days': refund_settings.cancellation_full_payment_partial_refund_days,
                            'cancellation_full_payment_partial_refund_percentage': float(refund_settings.cancellation_full_payment_partial_refund_percentage),
                            'cancellation_full_payment_minimal_refund_days': refund_settings.cancellation_full_payment_minimal_refund_days,
                            'cancellation_full_payment_minimal_refund_percentage': float(refund_settings.cancellation_full_payment_minimal_refund_percentage),

                            'cancellation_deposit_full_refund_days': refund_settings.cancellation_deposit_full_refund_days,
                            'cancellation_deposit_partial_refund_days': refund_settings.cancellation_deposit_partial_refund_days,
                            'cancellation_deposit_partial_refund_percentage': float(refund_settings.cancellation_deposit_partial_refund_percentage),
                            'cancellation_deposit_minimal_refund_days': refund_settings.cancellation_deposit_minimal_refund_days,
                            'cancellation_deposit_minimal_refund_percentage': float(refund_settings.cancellation_deposit_minimal_refund_percentage),

                            'refund_deducts_stripe_fee_policy': refund_settings.refund_deducts_stripe_fee_policy,
                            'stripe_fee_percentage_domestic': float(refund_settings.stripe_fee_percentage_domestic),
                            'stripe_fee_fixed_domestic': float(refund_settings.stripe_fee_fixed_domestic),
                            'stripe_fee_percentage_international': float(refund_settings.stripe_fee_percentage_international),
                            'stripe_fee_fixed_international': float(refund_settings.stripe_fee_fixed_international),
                        }
                    else:
                        payment_obj.refund_policy_snapshot = {}
                except Exception:
                    payment_obj.refund_policy_snapshot = {}

                payment_obj.save()

            send_booking_to_mechanicdesk(service_booking)

            temp_booking.delete()

            return service_booking

    except Exception:
        raise
