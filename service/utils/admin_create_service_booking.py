# service/utils/booking_creator.py
from service.models import ServiceBooking

def admin_create_service_booking(admin_booking_form_data, service_profile, customer_motorcycle, created_by_user):
    """
    Creates and saves a new ServiceBooking instance.
    admin_booking_form_data should be the cleaned_data from AdminBookingDetailsForm.
    """
    booking = ServiceBooking(
        service_type=admin_booking_form_data['service_type'],
        service_date=admin_booking_form_data['service_date'],
        dropoff_date=admin_booking_form_data['dropoff_date'],
        dropoff_time=admin_booking_form_data['dropoff_time'],
        customer_notes=admin_booking_form_data.get('customer_notes', ''),
        admin_notes=admin_booking_form_data.get('admin_notes', ''),
        booking_status=admin_booking_form_data['booking_status'],
        payment_status=admin_booking_form_data['payment_status'],
        estimated_pickup_date=admin_booking_form_data.get('estimated_pickup_date'),
        customer_profile=service_profile,
        customer_motorcycle=customer_motorcycle,
        created_by=created_by_user,

    )
    booking.save()
    return booking