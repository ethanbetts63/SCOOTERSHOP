from payments.models import Payment

def get_booking_from_payment(payment_obj: Payment):
    if payment_obj.service_booking:
        return payment_obj.service_booking, 'service_booking'
                                                      
    elif payment_obj.sales_booking:
        return payment_obj.sales_booking, 'sales_booking'
                                              
    return None, None
