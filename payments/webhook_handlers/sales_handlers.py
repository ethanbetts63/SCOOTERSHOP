from django.conf import settings
from decimal import Decimal

from inventory.models import TempSalesBooking, SalesBooking, SalesProfile
from payments.models import Payment
from inventory.utils.convert_temp_sales_booking import convert_temp_sales_booking
from mailer.utils import send_templated_email
from inventory.models import Motorcycle


def handle_sales_booking_succeeded(payment_obj: Payment, payment_intent_data: dict):
    if payment_obj.sales_booking:
        if payment_obj.status != payment_intent_data['status']:
            payment_obj.status = payment_intent_data['status']
            payment_obj.save()
        return

    try:
        temp_booking = payment_obj.temp_sales_booking

        if temp_booking is None:
            raise TempSalesBooking.DoesNotExist(f"TempSalesBooking for Payment ID {payment_obj.id} does not exist and no SalesBooking found.")

        booking_payment_status = 'unpaid'
        # Determine payment status based on whether a deposit was required and the amount paid
        if temp_booking.deposit_required_for_flow and (Decimal(payment_intent_data['amount_received']) / Decimal('100')) > 0:
            booking_payment_status = 'deposit_paid'
        elif (Decimal(payment_intent_data['amount_received']) / Decimal('100')) >= temp_booking.motorcycle.price: # Assuming full payment for simplicity or a defined 'full' amount
             booking_payment_status = 'paid'
        
        sales_booking = convert_temp_sales_booking(
            temp_booking=temp_booking,
            booking_payment_status=booking_payment_status,
            amount_paid_on_booking=Decimal(payment_intent_data['amount_received']) / Decimal('100'),
            stripe_payment_intent_id=payment_obj.stripe_payment_intent_id,
            payment_obj=payment_obj,
        )

        if payment_obj.status != payment_intent_data['status']:
            payment_obj.status = payment_intent_data['status']
            payment_obj.save()

        # Update motorcycle status to 'reserved' if a deposit was paid
        if sales_booking.payment_status in ['deposit_paid', 'paid'] and sales_booking.motorcycle:
            motorcycle = sales_booking.motorcycle
            motorcycle.status = 'reserved'
            motorcycle.is_available = False # Mark as unavailable for general sale
            motorcycle.save()

        email_context = {
            'sales_booking': sales_booking,
            'user': sales_booking.sales_profile.user if sales_booking.sales_profile and sales_booking.sales_profile.user else None,
            'sales_profile': sales_booking.sales_profile,
            'is_deposit_confirmed': booking_payment_status in ['deposit_paid', 'paid'],
        }

        user_email = sales_booking.sales_profile.user.email if sales_booking.sales_profile.user else sales_booking.sales_profile.email
        if user_email:
            send_templated_email(
                recipient_list=[user_email],
                subject=f"Your Sales Booking Confirmation - {sales_booking.sales_booking_reference}",
                template_name='sales_booking_confirmation_user.html', # This template needs to be created
                context=email_context,
                booking=sales_booking
            )

        if settings.ADMIN_EMAIL:
            send_templated_email(
                recipient_list=[settings.ADMIN_EMAIL],
                subject=f"New Sales Booking (Online) - {sales_booking.sales_booking_reference}",
                template_name='sales_booking_confirmation_admin.html', # This template needs to be created
                context=email_context,
                booking=sales_booking
            )

    except TempSalesBooking.DoesNotExist as e:
        raise
    except Exception as e:
        raise
