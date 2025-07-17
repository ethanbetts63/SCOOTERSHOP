from django.db import transaction
from inventory.models import SalesBooking, InventorySettings
from inventory.utils.send_sales_booking_to_mechanicdesk import (
    send_sales_booking_to_mechanicdesk,
)


def convert_temp_sales_booking(
    temp_booking,
    booking_payment_status,
    amount_paid_on_booking,
    stripe_payment_intent_id=None,
    payment_obj=None,
):
    try:
        with transaction.atomic():
            inventory_settings = InventorySettings.objects.first()

            currency_code = "AUD"
            if inventory_settings:
                currency_code = inventory_settings.currency_code

            sales_booking = SalesBooking.objects.create(
                motorcycle=temp_booking.motorcycle,
                sales_profile=temp_booking.sales_profile,
                amount_paid=amount_paid_on_booking,
                payment_status=booking_payment_status,
                currency=currency_code,
                stripe_payment_intent_id=stripe_payment_intent_id,
                appointment_date=temp_booking.appointment_date,
                appointment_time=temp_booking.appointment_time,
                booking_status="pending_confirmation",
                customer_notes=temp_booking.customer_notes,
                payment=payment_obj,
                sales_terms_version=temp_booking.sales_terms_version,
            )

            if payment_obj:
                payment_obj.amount = amount_paid_on_booking
                payment_obj.currency = currency_code
                payment_obj.status = booking_payment_status
                payment_obj.stripe_payment_intent_id = stripe_payment_intent_id
                payment_obj.sales_booking = sales_booking
                payment_obj.sales_customer_profile = sales_booking.sales_profile

                if (
                    hasattr(payment_obj, "temp_sales_booking")
                    and payment_obj.temp_sales_booking
                ):
                    payment_obj.temp_sales_booking = None

                payment_obj.save()

            temp_booking.delete()

            if (
                inventory_settings
                and inventory_settings.send_sales_booking_to_mechanic_desk
            ):
                try:
                    send_success = send_sales_booking_to_mechanicdesk(sales_booking)
                except Exception:
                    pass

            return sales_booking

    except Exception as e:
        raise e
