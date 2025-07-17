from decimal import Decimal
from django.core.exceptions import ObjectDoesNotExist


def calculate_service_total(temp_booking):
    try:
        if temp_booking.service_type:
            return temp_booking.service_type.base_price
    except ObjectDoesNotExist:
        pass
    return Decimal("0.00")
