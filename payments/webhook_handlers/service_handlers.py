from django.conf import settings
import logging

logger = logging.getLogger(__name__)
from decimal import Decimal
from service.models import TempServiceBooking
from payments.models import Payment
from service.utils.convert_temp_service_booking import convert_temp_service_booking
from mailer.utils import send_templated_email
from dashboard.models import SiteSettings


def handle_service_booking_succeeded(payment_obj: Payment, payment_intent_data: dict):
    if payment_obj.service_booking:
        if payment_obj.status != payment_intent_data["status"]:
            payment_obj.status = payment_intent_data["status"]
            payment_obj.save()
        return

    try:
        temp_booking = payment_obj.temp_service_booking

        if temp_booking is None:
            raise TempServiceBooking.DoesNotExist(
                f"TempServiceBooking for Payment ID {payment_obj.id} does not exist and no ServiceBooking found."
            )
        booking_payment_status = "unpaid"
        if temp_booking.payment_method == "online_full":
            booking_payment_status = "paid"
        elif temp_booking.payment_method == "online_deposit":
            booking_payment_status = "deposit_paid"

        try:
            service_booking = convert_temp_service_booking(
                temp_booking=temp_booking,
                payment_method=temp_booking.payment_method,
                booking_payment_status=booking_payment_status,
                booking_status="pending",
                amount_paid_on_booking=Decimal(payment_intent_data["amount_received"])
                / Decimal("100"),
                calculated_total_on_booking=temp_booking.calculated_total,
                stripe_payment_intent_id=payment_obj.stripe_payment_intent_id,
                payment_obj=payment_obj,
            )
        except OSError as e:
            logger.error(
                f"Webhook Error: OSError converting temp service booking for payment {payment_obj.id}. Error: {e}"
            )
            raise

        if payment_obj.status != payment_intent_data["status"]:
            payment_obj.status = payment_intent_data["status"]
            payment_obj.save()

        service_profile = service_booking.service_profile
        user_email = service_profile.email
        site_settings = SiteSettings.get_settings()

        if user_email:
            send_templated_email(
                recipient_list=[user_email],
                subject=f"Your Service Booking Request Submitted - {service_booking.service_booking_reference}",
                template_name="user_service_booking_request_submitted.html",
                context={
                    "booking": service_booking,
                    "profile": service_profile,
                    "SITE_DOMAIN": settings.SITE_DOMAIN,
                    "SITE_SCHEME": settings.SITE_SCHEME,
                    "site_settings": site_settings,
                },
                booking=service_booking,
                profile=service_profile,
            )

        if settings.ADMIN_EMAIL:
            send_templated_email(
                recipient_list=[settings.ADMIN_EMAIL],
                subject=f"New Service Booking (Online) - {service_booking.service_booking_reference}",
                template_name="admin_service_booking_confirmation.html",
                context={
                    "booking": service_booking,
                    "profile": service_profile,
                    "SITE_DOMAIN": settings.SITE_DOMAIN,
                    "SITE_SCHEME": settings.SITE_SCHEME,
                    "site_settings": site_settings,
                },
                booking=service_booking,
                profile=service_profile,
            )

    except TempServiceBooking.DoesNotExist as e:
        logger.warning(
            f"Webhook Info: TempServiceBooking not found for payment {payment_obj.id}, possibly already processed. Error: {e}"
        )
        pass

    except Exception as e:
        logger.error(
            f"Webhook Error: Unhandled exception in service booking success handler for payment {payment_obj.id}. Error: {e}"
        )
        raise
