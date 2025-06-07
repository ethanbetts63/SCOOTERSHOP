# payments/webhook_handlers/service_handlers.py
from django.conf import settings
from decimal import Decimal

# Import models specific to the service app
from service.models import TempServiceBooking, ServiceBooking, ServiceProfile

# Import Payment model from payments app
from payments.models import Payment

# Import the centralized converter function
from service.utils.convert_temp_service_booking import convert_temp_service_booking

# Import the email sending utility
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
    print(f"DEBUG: Entering handle_service_booking_succeeded for Payment ID: {payment_obj.id}")

    try:
        # The related name from Payment to TempServiceBooking is 'payment_for_temp_service'
        # but the field name on Payment is 'temp_service_booking'
        temp_booking = payment_obj.temp_service_booking

        if temp_booking is None:
            print(f"ERROR: TempServiceBooking not found for Payment ID {payment_obj.id}. Cannot finalize booking.")
            raise TempServiceBooking.DoesNotExist(f"TempServiceBooking for Payment ID {payment_obj.id} does not exist.")

        # Determine payment_status for the ServiceBooking based on the original payment option
        if temp_booking.payment_option == 'online_full':
            booking_payment_status = 'paid'
        elif temp_booking.payment_option == 'online_deposit':
            booking_payment_status = 'deposit_paid'
        elif temp_booking.payment_option == 'in_store_full':
            booking_payment_status = 'unpaid'
        else:
            booking_payment_status = 'unpaid'
            print(f"WARNING: Unexpected payment_option '{temp_booking.payment_option}' for TempServiceBooking {temp_booking.pk}. Defaulting to 'unpaid'.")

        # Use the centralized converter function
        service_booking = convert_temp_service_booking(
            temp_booking=temp_booking,
            payment_method=temp_booking.payment_option,
            booking_payment_status=booking_payment_status,
            amount_paid_on_booking=Decimal(payment_intent_data['amount_received']) / Decimal('100'),
            calculated_total_on_booking=temp_booking.calculated_total,
            stripe_payment_intent_id=payment_obj.stripe_payment_intent_id,
            payment_obj=payment_obj,
        )

        # The payment_obj's status is updated by the converter. We can double-check here.
        if payment_obj.status != payment_intent_data['status']:
            payment_obj.status = payment_intent_data['status']
            payment_obj.save()
            print(f"DEBUG: Updated Payment {payment_obj.id} status to {payment_obj.status}.")

        # --- Email Sending for Online Service Booking Confirmation ---
        email_context = {
            'service_booking': service_booking,
            'user': service_booking.service_profile.user if service_booking.service_profile and service_booking.service_profile.user else None,
            'service_profile': service_booking.service_profile,
            'is_in_store': False,
        }

        # Send confirmation email to the user
        user_email = service_booking.service_profile.user.email if service_booking.service_profile.user else service_booking.service_profile.email
        if user_email:
            send_templated_email(
                recipient_list=[user_email],
                subject=f"Your Service Booking Confirmation - {service_booking.service_booking_reference}",
                template_name='service_booking_confirmation_user.html', # Assumes this template exists
                context=email_context,
                booking=service_booking
            )
            print(f"DEBUG: Sent user service booking confirmation email to {user_email}.")

        # Send notification email to the admin
        if settings.ADMIN_EMAIL:
            send_templated_email(
                recipient_list=[settings.ADMIN_EMAIL],
                subject=f"New Service Booking (Online) - {service_booking.service_booking_reference}",
                template_name='service_booking_confirmation_admin.html', # Assumes this template exists
                context=email_context,
                booking=service_booking
            )
            print(f"DEBUG: Sent admin service booking confirmation email.")
        # --- End Email Sending ---

    except TempServiceBooking.DoesNotExist:
        print(f"ERROR: TempServiceBooking not found for Payment ID {payment_obj.id} in handle_service_booking_succeeded. Cannot finalize booking.")
        raise
    except Exception as e:
        print(f"CRITICAL ERROR: Critical error finalizing service booking for Payment ID {payment_obj.id} in handle_service_booking_succeeded: {e}")
        raise

