# service/utils/calculate_estimated_pickup_date.py

from datetime import timedelta
# No specific model imports needed here to keep it generic

def calculate_estimated_pickup_date(booking_instance):
    """
    Calculates and assigns the estimated pickup date for a given booking instance.

    This function is designed to work with either a TempServiceBooking or
    a ServiceBooking instance, as long as they have the following attributes:
    - service_date (datetime.date)
    - service_type (ForeignKey to ServiceType model, which has estimated_duration)
    - estimated_pickup_date (DateField)

    The estimated pickup date is determined by adding the service type's
    'estimated_duration' (in days) to the 'service_date' of the booking instance.

    Args:
        booking_instance (object): An instance of TempServiceBooking or ServiceBooking.

    Returns:
        datetime.date: The calculated estimated pickup date.
                       Returns None if service_type or service_date is missing.
    """
    if not hasattr(booking_instance, 'service_type') or not booking_instance.service_type:
        print(f"Warning: Booking instance {booking_instance} has no associated service_type. Cannot calculate estimated pickup date.")
        return None

    if not hasattr(booking_instance, 'service_date') or not booking_instance.service_date:
        print(f"Warning: Booking instance {booking_instance} has no service_date. Cannot calculate estimated pickup date.")
        return None

    # Get the estimated duration from the associated ServiceType
    # Ensure service_type.estimated_duration is an integer as defined in ServiceType model
    estimated_duration_days = booking_instance.service_type.estimated_duration

    # Calculate the estimated pickup date
    estimated_pickup_date = booking_instance.service_date + timedelta(days=estimated_duration_days)

    # Assign the calculated date back to the booking instance object
    booking_instance.estimated_pickup_date = estimated_pickup_date

    # Save the booking instance to persist the change.
    # Use update_fields for efficiency, specifically updating 'estimated_pickup_date'.
    booking_instance.save(update_fields=['estimated_pickup_date'])

    return estimated_pickup_date

