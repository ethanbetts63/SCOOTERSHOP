from datetime import timedelta


def calculate_estimated_pickup_date(booking_instance):
    if (
        not hasattr(booking_instance, "service_type")
        or not booking_instance.service_type
    ):
        return None

    if (
        not hasattr(booking_instance, "service_date")
        or not booking_instance.service_date
    ):
        return None

    estimated_duration_days = booking_instance.service_type.estimated_duration

    estimated_pickup_date = booking_instance.service_date + timedelta(
        days=estimated_duration_days
    )

    booking_instance.estimated_pickup_date = estimated_pickup_date

    booking_instance.save(update_fields=["estimated_pickup_date"])

    return estimated_pickup_date
