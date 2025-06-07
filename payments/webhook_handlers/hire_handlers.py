from django.db import transaction
from decimal import Decimal
from django.conf import settings

from hire.models import TempHireBooking, HireBooking, DriverProfile

from payments.models import Payment

from hire.temp_hire_converter import convert_temp_to_hire_booking

from mailer.utils import send_templated_email


def handle_hire_booking_succeeded(payment_obj: Payment, payment_intent_data: dict):
    """
    Handles the business logic for a successful payment_intent.succeeded event
    specifically for a 'hire_booking'.

    This function is responsible for:
    1. Utilizing the centralized converter to turn TempHireBooking into HireBooking.
    2. Updating the Payment object's status to reflect the successful payment.
    3. Sending confirmation emails to the user and admin.

    Args:
        payment_obj (Payment): The Payment model instance linked to this intent.
        payment_intent_data (dict): The data object from the Stripe PaymentIntent event.
    """

    try:
        temp_booking = payment_obj.temp_hire_booking

        if temp_booking is None:
            raise TempHireBooking.DoesNotExist(f"TempHireBooking for Payment ID {payment_obj.id} does not exist.")

        if temp_booking.payment_option == 'online_full':
            hire_payment_status = 'paid'
        elif temp_booking.payment_option == 'online_deposit':
            hire_payment_status = 'deposit_paid'
        elif temp_booking.payment_option == 'in_store_full':
            hire_payment_status = 'unpaid'
        else:
            hire_payment_status = 'unpaid'


        hire_booking = convert_temp_to_hire_booking(
            temp_booking=temp_booking,
            payment_method=temp_booking.payment_option,
            booking_payment_status=hire_payment_status,
            amount_paid_on_booking=Decimal(payment_intent_data['amount_received']) / Decimal('100'),
            stripe_payment_intent_id=payment_obj.stripe_payment_intent_id,
            payment_obj=payment_obj,
        )

        if payment_obj.status != payment_intent_data['status']:
            payment_obj.status = payment_intent_data['status']
            payment_obj.save()

        email_context = {
            'hire_booking': hire_booking,
            'user': hire_booking.driver_profile.user if hire_booking.driver_profile and hire_booking.driver_profile.user else None,
            'driver_profile': hire_booking.driver_profile,
            'is_in_store': False,
        }

        user_email = hire_booking.driver_profile.user.email if hire_booking.driver_profile.user else hire_booking.driver_profile.email
        if user_email:
            send_templated_email(
                recipient_list=[user_email],
                subject=f"Your Motorcycle Hire Booking Confirmation - {hire_booking.booking_reference}",
                template_name='booking_confirmation_user.html',
                context=email_context,
                user=hire_booking.driver_profile.user if hire_booking.driver_profile and hire_booking.driver_profile.user else None,
                driver_profile=hire_booking.driver_profile,
                booking=hire_booking
            )

        if settings.ADMIN_EMAIL:
            send_templated_email(
                recipient_list=[settings.ADMIN_EMAIL],
                subject=f"New Motorcycle Hire Booking (Online) - {hire_booking.booking_reference}",
                template_name='booking_confirmation_admin.html',
                context=email_context,
                booking=hire_booking
            )

    except TempHireBooking.DoesNotExist:
        raise
    except Exception as e:
        raise
