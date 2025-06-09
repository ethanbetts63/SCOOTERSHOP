# payments/utils/booking_payment_updater.py

from decimal import Decimal
from payments.models import Payment
from hire.models import HireBooking
from service.models import ServiceBooking


def update_associated_bookings_and_payments(payment_obj: Payment, booking_obj, booking_type_str: str, total_refunded_amount: Decimal):
    if booking_obj:
        booking_obj.amount_paid = payment_obj.amount - total_refunded_amount

        if booking_obj.amount_paid <= 0:
            booking_obj.payment_status = 'refunded'
        elif booking_obj.amount_paid < payment_obj.amount:
            booking_obj.payment_status = 'partially_refunded'
        else:
            booking_obj.payment_status = 'paid'

        if booking_type_str == 'service_booking':
            if booking_obj.booking_status == 'declined' and booking_obj.payment_status == 'refunded':
                booking_obj.booking_status = 'DECLINED_REFUNDED'
        elif booking_type_str == 'hire_booking':
            if booking_obj.payment_status == 'refunded':
                booking_obj.status = 'cancelled'

        booking_obj.save()

    payment_obj.refunded_amount = total_refunded_amount
    if payment_obj.refunded_amount >= payment_obj.amount:
        payment_obj.status = 'refunded'
    elif payment_obj.refunded_amount > 0:
        payment_obj.status = 'partially_refunded'
    else:
        payment_obj.status = 'succeeded'

    payment_obj.save()
