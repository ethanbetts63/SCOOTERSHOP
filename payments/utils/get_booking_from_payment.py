# payments/utils/booking_helpers.py

from payments.models import Payment
from inventory.models import SalesBooking # Import SalesBooking

def get_booking_from_payment(payment_obj: Payment):
    # Check if the payment is linked to a HireBooking
    if payment_obj.hire_booking:
        return payment_obj.hire_booking, 'hire_booking'
    # Check if the payment is linked to a ServiceBooking
    elif payment_obj.service_booking:
        return payment_obj.service_booking, 'service_booking'
    # Check if the payment is linked to a SalesBooking
    elif payment_obj.sales_booking:
        return payment_obj.sales_booking, 'sales_booking'
    # If no booking type is found, return None
    return None, None
