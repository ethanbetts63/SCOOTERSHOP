from django.conf import settings
from decimal import Decimal

from service.models import TempServiceBooking, ServiceBooking, ServiceProfile

from payments.models import Payment

from service.utils.convert_temp_service_booking import convert_temp_service_booking

from mailer.utils import send_templated_email

def handle_service_booking_succeeded(payment_obj: Payment, payment_intent_data: dict):
    """
    Handles the business logic for a successful payment_intent.succeeded event
    specifically for a 'service_booking'.

    This function is responsible for:
    1. Utilizing the centralized converter to turn TempServiceBooking into ServiceBooking.
    2. Updating the Payment object's status to reflect the successful payment.
    3. Sending confirmation emails to the user and admin.

    Args:
        payment_obj (Payment): The Payment model instance linked to this intent.
        payment_intent_data (dict): The data object from the Stripe PaymentIntent event.
    """
    print("DEBUG: handle_service_booking_succeeded - Function entered.")
    print(f"DEBUG: handle_service_booking_succeeded - payment_obj ID: {payment_obj.id}")
    print(f"DEBUG: handle_service_booking_succeeded - payment_intent_data: {payment_intent_data}")

    try:
        temp_booking = payment_obj.temp_service_booking
        print(f"DEBUG: handle_service_booking_succeeded - temp_booking retrieved: {temp_booking}")

        if temp_booking is None:
            print(f"ERROR: handle_service_booking_succeeded - TempServiceBooking for Payment ID {payment_obj.id} does not exist.")
            raise TempServiceBooking.DoesNotExist(f"TempServiceBooking for Payment ID {payment_obj.id} does not exist.")

        booking_payment_status = 'unpaid' # Default to unpaid
        if temp_booking.payment_option == 'online_full':
            booking_payment_status = 'paid'
        elif temp_booking.payment_option == 'online_deposit':
            booking_payment_status = 'deposit_paid'
        elif temp_booking.payment_option == 'in_store_full':
            booking_payment_status = 'unpaid' # Already handled by step 5, but good to keep consistent
        
        print(f"DEBUG: handle_service_booking_succeeded - Determined booking_payment_status: {booking_payment_status}")
        print(f"DEBUG: handle_service_booking_succeeded - Arguments for convert_temp_service_booking:")
        print(f"  temp_booking: {temp_booking}")
        print(f"  payment_method: {temp_booking.payment_option}")
        print(f"  booking_payment_status: {booking_payment_status}")
        print(f"  amount_paid_on_booking: {Decimal(payment_intent_data['amount_received']) / Decimal('100')}")
        print(f"  calculated_total_on_booking: {temp_booking.calculated_total}")
        print(f"  stripe_payment_intent_id: {payment_obj.stripe_payment_intent_id}")
        print(f"  payment_obj: {payment_obj}")


        service_booking = convert_temp_service_booking(
            temp_booking=temp_booking,
            payment_method=temp_booking.payment_option,
            booking_payment_status=booking_payment_status,
            amount_paid_on_booking=Decimal(payment_intent_data['amount_received']) / Decimal('100'),
            calculated_total_on_booking=temp_booking.calculated_total,
            stripe_payment_intent_id=payment_obj.stripe_payment_intent_id,
            payment_obj=payment_obj,
        )
        print(f"DEBUG: handle_service_booking_succeeded - service_booking created: {service_booking}")
        print(f"DEBUG: handle_service_booking_succeeded - service_booking payment_status: {service_booking.payment_status}")


        if payment_obj.status != payment_intent_data['status']:
            print(f"DEBUG: handle_service_booking_succeeded - Updating payment_obj status from {payment_obj.status} to {payment_intent_data['status']}")
            payment_obj.status = payment_intent_data['status']
            payment_obj.save()
            print("DEBUG: handle_service_booking_succeeded - payment_obj status updated and saved.")


        email_context = {
            'service_booking': service_booking,
            'user': service_booking.service_profile.user if service_booking.service_profile and service_booking.service_profile.user else None,
            'service_profile': service_booking.service_profile,
            'is_in_store': False,
        }

        user_email = service_booking.service_profile.user.email if service_booking.service_profile.user else service_booking.service_profile.email
        if user_email:
            print(f"DEBUG: handle_service_booking_succeeded - Attempting to send user confirmation email to: {user_email}")
            send_templated_email(
                recipient_list=[user_email],
                subject=f"Your Service Booking Confirmation - {service_booking.service_booking_reference}",
                template_name='service_booking_confirmation_user.html',
                context=email_context,
                booking=service_booking
            )
            print("DEBUG: handle_service_booking_succeeded - User confirmation email sent successfully (or attempted).")

        if settings.ADMIN_EMAIL:
            print(f"DEBUG: handle_service_booking_succeeded - Attempting to send admin notification email to: {settings.ADMIN_EMAIL}")
            send_templated_email(
                recipient_list=[settings.ADMIN_EMAIL],
                subject=f"New Service Booking (Online) - {service_booking.service_booking_reference}",
                template_name='service_booking_confirmation_admin.html',
                context=email_context,
                booking=service_booking
            )
            print("DEBUG: handle_service_booking_succeeded - Admin notification email sent successfully (or attempted).")
        else:
            print("DEBUG: handle_service_booking_succeeded - ADMIN_EMAIL is not configured in settings. Skipping admin email.")


    except TempServiceBooking.DoesNotExist as e:
        print(f"ERROR: handle_service_booking_succeeded - TempServiceBooking.DoesNotExist: {e}")
        raise
    except Exception as e:
        print(f"ERROR: handle_service_booking_succeeded - An unexpected error occurred: {e}")
        raise
    
    print("DEBUG: handle_service_booking_succeeded - Function exited.")
