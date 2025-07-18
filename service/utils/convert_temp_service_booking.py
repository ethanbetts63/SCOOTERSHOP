from django.db import transaction
from decimal import Decimal
from service.utils.send_booking_to_mechanicdesk import send_booking_to_mechanicdesk
from service.models import ServiceBooking, ServiceSettings


def convert_temp_service_booking(
    temp_booking,
    payment_method,
    booking_payment_status,
    amount_paid_on_booking,
    calculated_total_on_booking,
    booking_status="confirmed",
    stripe_payment_intent_id=None,
    payment_obj=None,
):
    try:
        with transaction.atomic():
            service_settings = ServiceSettings.objects.first()

            currency_code = "AUD"
            if service_settings:
                currency_code = service_settings.currency_code

            service_booking = ServiceBooking.objects.create(
                service_type=temp_booking.service_type,
                service_profile=temp_booking.service_profile,
                customer_motorcycle=temp_booking.customer_motorcycle,
                calculated_total=calculated_total_on_booking,
                calculated_deposit_amount=(
                    temp_booking.calculated_deposit_amount
                    if temp_booking.calculated_deposit_amount is not None
                    else Decimal("0.00")
                ),
                amount_paid=amount_paid_on_booking,
                payment_status=booking_payment_status,
                payment_method=payment_method,
                currency=currency_code,
                stripe_payment_intent_id=stripe_payment_intent_id,
                service_date=temp_booking.service_date,
                dropoff_date=temp_booking.dropoff_date,
                dropoff_time=temp_booking.dropoff_time,
                after_hours_drop_off=temp_booking.after_hours_drop_off,
                estimated_pickup_date=temp_booking.estimated_pickup_date,
                booking_status=booking_status,
                customer_notes=temp_booking.customer_notes,
                service_terms_version=temp_booking.service_terms_version,
                payment=payment_obj,
            )

            if payment_obj:
                payment_obj.amount = amount_paid_on_booking

                payment_obj.currency = currency_code
                payment_obj.status = booking_payment_status
                payment_obj.stripe_payment_intent_id = stripe_payment_intent_id
                payment_obj.service_booking = service_booking
                payment_obj.service_customer_profile = service_booking.service_profile

                if (
                    hasattr(payment_obj, "temp_service_booking")
                    and payment_obj.temp_service_booking
                ):
                    payment_obj.temp_service_booking = None

                payment_obj.save()

            try:
                send_booking_to_mechanicdesk(service_booking)
            except OSError as e:
                logger.error(f"OSError sending booking to MechanicDesk: {e}")

            temp_booking.delete()

            return service_booking

    except Exception:
        raise
