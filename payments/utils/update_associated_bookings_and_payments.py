# payments/utils/booking_payment_updater.py

from decimal import Decimal
from payments.models import Payment
from hire.models import HireBooking
from service.models import ServiceBooking
from inventory.models import SalesBooking # Import SalesBooking


def update_associated_bookings_and_payments(payment_obj: Payment, booking_obj, booking_type_str: str, total_refunded_amount: Decimal):
    if booking_obj:
        # Ensure amount_paid does not go below zero, even if over-refunded
        booking_obj.amount_paid = max(Decimal('0.00'), payment_obj.amount - total_refunded_amount)

        if booking_obj.amount_paid <= 0:
            booking_obj.payment_status = 'refunded'
        elif booking_obj.amount_paid < payment_obj.amount:
            booking_obj.payment_status = 'partially_refunded'
        else:
            # If the amount_paid is still equal to the original payment amount,
            # it means no refund or a full refund that brought it back to original.
            # So, status should remain 'paid' or 'succeeded' for the payment.
            booking_obj.payment_status = 'paid'

        if booking_type_str == 'service_booking':
            if booking_obj.booking_status == 'declined' and booking_obj.payment_status == 'refunded':
                booking_obj.booking_status = 'DECLINED_REFUNDED'
        elif booking_type_str == 'hire_booking':
            if booking_obj.payment_status == 'refunded':
                booking_obj.status = 'cancelled'
        elif booking_type_str == 'sales_booking': # Added SalesBooking logic
            # For sales bookings, if fully refunded, change status to 'declined_refunded'
            # Or if it was already cancelled/declined and now refunded.
            if booking_obj.payment_status == 'refunded' and booking_obj.booking_status in ['pending_confirmation', 'confirmed', 'enquired']:
                booking_obj.booking_status = 'declined_refunded'
            elif booking_obj.payment_status == 'refunded' and booking_obj.booking_status in ['cancelled', 'declined', 'no_show']:
                 # If sales booking was already cancelled/declined/no_show, and now payment is refunded
                 booking_obj.booking_status = 'declined_refunded'
            elif booking_obj.payment_status == 'partially_refunded':
                # If a partial refund, keep the original booking status, but indicate partial refund
                pass # No change to booking_status for partial refund on sales

        booking_obj.save()

    payment_obj.refunded_amount = total_refunded_amount
    if payment_obj.refunded_amount >= payment_obj.amount:
        payment_obj.status = 'refunded'
    elif payment_obj.refunded_amount > 0:
        payment_obj.status = 'partially_refunded'
    else:
        payment_obj.status = 'succeeded' # If refunded_amount is 0, status should be succeeded (no refund applied)

    payment_obj.save()
