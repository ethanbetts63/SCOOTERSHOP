import decimal
from service.models import ServiceSettings

def calculate_deposit_amount(temp_booking):
    service_settings = ServiceSettings.objects.first()

    if not service_settings or not service_settings.enable_deposit:
        return decimal.Decimal('0.00')

    total_amount = temp_booking.service_type.base_price

    deposit_amount = decimal.Decimal('0.00')

    if service_settings.deposit_calc_method == 'FLAT_FEE':
        deposit_amount = service_settings.deposit_flat_fee_amount
    elif service_settings.deposit_calc_method == 'PERCENTAGE':
        if total_amount is not None and service_settings.deposit_percentage is not None:
            deposit_amount = total_amount * service_settings.deposit_percentage

    return max(deposit_amount, decimal.Decimal('0.00'))

