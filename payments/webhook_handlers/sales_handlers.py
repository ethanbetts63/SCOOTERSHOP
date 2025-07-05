from django.conf import settings
from decimal import Decimal

from inventory.models import TempSalesBooking
from payments.models import Payment
from inventory.utils.convert_temp_sales_booking import convert_temp_sales_booking
from mailer.utils import send_templated_email


def handle_sales_booking_succeeded(payment_obj: Payment, payment_intent_data: dict):
    if payment_obj.sales_booking:
        if payment_obj.status != payment_intent_data["status"]:
            payment_obj.status = payment_intent_data["status"]
            payment_obj.save()
        return

    try:
        temp_booking = payment_obj.temp_sales_booking

        if temp_booking is None:
            raise TempSalesBooking.DoesNotExist(
                f"TempSalesBooking for Payment ID {payment_obj.id} does not exist and no SalesBooking found."
            )

        booking_payment_status = "unpaid"
        if (
            temp_booking.deposit_required_for_flow
            and (Decimal(payment_intent_data["amount_received"]) / Decimal("100")) > 0
        ):
            booking_payment_status = "deposit_paid"

        sales_booking = convert_temp_sales_booking(
            temp_booking=temp_booking,
            booking_payment_status=booking_payment_status,
            amount_paid_on_booking=Decimal(payment_intent_data["amount_received"])
            / Decimal("100"),
            stripe_payment_intent_id=payment_obj.stripe_payment_intent_id,
            payment_obj=payment_obj,
        )

        if payment_obj.status != payment_intent_data["status"]:
            payment_obj.status = payment_intent_data["status"]
            payment_obj.save()

        if sales_booking.payment_status == "deposit_paid" and sales_booking.motorcycle:
            motorcycle = sales_booking.motorcycle

            if motorcycle.conditions.filter(name="new").exists():
                if motorcycle.quantity is not None and motorcycle.quantity > 0:
                    motorcycle.quantity -= 1
                    if motorcycle.quantity == 0:
                        motorcycle.is_available = False
                        motorcycle.status = "sold"
                else:
                    pass
            else:
                motorcycle.status = "reserved"
                motorcycle.is_available = False

            motorcycle.save()

        sales_profile = sales_booking.sales_profile
        email_context = {
            "sales_booking": sales_booking,
            "user": (
                sales_profile.user if sales_profile and sales_profile.user else None
            ),
            "sales_profile": sales_profile,
            "is_deposit_confirmed": sales_booking.payment_status == "deposit_paid",
        }

        user_email = (
            sales_profile.user.email if sales_profile.user else sales_profile.email
        )
        if user_email:
            send_templated_email(
                recipient_list=[user_email],
                subject=f"Your Sales Booking Confirmation - {sales_booking.sales_booking_reference}",
                template_name="user_sales_booking_confirmation.html",
                context=email_context,
                booking=sales_booking,
                profile=sales_profile,
            )

        if settings.ADMIN_EMAIL:
            send_templated_email(
                recipient_list=[settings.ADMIN_EMAIL],
                subject=f"New Sales Booking (Online) - {sales_booking.sales_booking_reference}",
                template_name="admin_sales_booking_confirmation.html",
                context=email_context,
                booking=sales_booking,
                profile=sales_profile,
            )

    except TempSalesBooking.DoesNotExist:
        raise
    except Exception:
        raise
