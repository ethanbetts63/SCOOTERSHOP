                                  
from service.models import ServiceBooking
from service.utils.send_booking_to_mechanicdesk import send_booking_to_mechanicdesk

def admin_create_service_booking(admin_booking_form_data, service_profile, customer_motorcycle):                                    
    
    booking = ServiceBooking(
        service_type=admin_booking_form_data['service_type'],
        service_date=admin_booking_form_data['service_date'],
        dropoff_date=admin_booking_form_data['dropoff_date'],
        dropoff_time=admin_booking_form_data['dropoff_time'],
        customer_notes=admin_booking_form_data.get('customer_notes', ''),
        booking_status=admin_booking_form_data['booking_status'],
        payment_status=admin_booking_form_data['payment_status'],
        estimated_pickup_date=admin_booking_form_data.get('estimated_pickup_date'),
        service_profile=service_profile,
        customer_motorcycle=customer_motorcycle,
    )
    booking.save()

    send_booking_to_mechanicdesk(booking)
    return booking
