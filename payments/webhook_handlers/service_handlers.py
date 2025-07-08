from django.conf import settings
from decimal import Decimal
from service.models import TempServiceBooking
from payments.models import Payment
from service.utils.convert_temp_service_booking import convert_temp_service_booking
from mailer.utils import send_templated_email


def handle_service_booking_succeeded(payment_obj: Payment, payment_intent_data: dict):
    print("--- handle_service_booking_succeeded START ---")
    print(f"Payment object ID: {payment_obj.id}")
    print(f"Payment object status: {payment_obj.status}")
    print(f"Payment intent status: {payment_intent_data.get('status')}")

    if payment_obj.service_booking:
        print("Service booking already exists on payment object. Updating status if needed.")
        if payment_obj.status != payment_intent_data["status"]:
            payment_obj.status = payment_intent_data["status"]
            payment_obj.save()
            print("Payment object status updated.")
        print("--- handle_service_booking_succeeded END (already processed) ---")
        return

    try:
        temp_booking = payment_obj.temp_service_booking
        print(f"Temp booking object: {temp_booking}")

        if temp_booking is None:
            print("ERROR: TempServiceBooking not found on payment object.")
            raise TempServiceBooking.DoesNotExist(
                f"TempServiceBooking for Payment ID {payment_obj.id} does not exist and no ServiceBooking found."
            )

        print(f"Temp booking ID: {temp_booking.id}")
        print(f"Temp booking payment method: {temp_booking.payment_method}")
        print(f"Temp booking after hours drop off: {temp_booking.after_hours_drop_off}")
        print(f"Temp booking dropoff date: {temp_booking.dropoff_date}")
        print(f"Temp booking dropoff time: {temp_booking.dropoff_time}")


        booking_payment_status = "unpaid"
        if temp_booking.payment_method == "online_full":
            booking_payment_status = "paid"
        elif temp_booking.payment_method == "online_deposit":
            booking_payment_status = "deposit_paid"
        
        print(f"Calculated booking_payment_status: {booking_payment_status}")
        print("Calling convert_temp_service_booking...")

        service_booking = convert_temp_service_booking(
            temp_booking=temp_booking,
            payment_method=temp_booking.payment_method,
            booking_payment_status=booking_payment_status,
            amount_paid_on_booking=Decimal(payment_intent_data["amount_received"])
            / Decimal("100"),
            calculated_total_on_booking=temp_booking.calculated_total,
            stripe_payment_intent_id=payment_obj.stripe_payment_intent_id,
            payment_obj=payment_obj,
        )
        
        print(f"Successfully converted temp booking to service booking. Service booking ID: {service_booking.id}")

        if payment_obj.status != payment_intent_data["status"]:
            payment_obj.status = payment_intent_data["status"]
            payment_obj.save()
            print("Payment object status updated after conversion.")

        service_profile = service_booking.service_profile
        user_email = service_profile.email
        
        print(f"User email for confirmation: {user_email}")

        if user_email:
            print("Sending user confirmation email...")
            send_templated_email(
                recipient_list=[user_email],
                subject=f"Your Service Booking Confirmation - {service_booking.service_booking_reference}",
                template_name="user_service_booking_confirmation.html",
                context={
                    "booking": service_booking,
                    "profile": service_profile,
                },
                booking=service_booking,
                profile=service_profile,
            )
            print("User confirmation email sent.")

        if settings.ADMIN_EMAIL:
            print("Sending admin confirmation email...")
            send_templated_email(
                recipient_list=[settings.ADMIN_EMAIL],
                subject=f"New Service Booking (Online) - {service_booking.service_booking_reference}",
                template_name="admin_service_booking_confirmation.html",
                context={
                    "booking": service_booking,
                    "profile": service_profile,
                },
                booking=service_booking,
                profile=service_profile,
            )
            print("Admin confirmation email sent.")
        
        print("--- handle_service_booking_succeeded END (SUCCESS) ---")

    except TempServiceBooking.DoesNotExist as e:
        print(f"ERROR: TempServiceBooking.DoesNotExist exception: {e}")
        print("--- handle_service_booking_succeeded END (ERROR) ---")
        raise
    except Exception as e:
        print(f"ERROR: An unexpected exception occurred: {e}")
        import traceback
        print(traceback.format_exc())
        print("--- handle_service_booking_succeeded END (ERROR) ---")
        raise
