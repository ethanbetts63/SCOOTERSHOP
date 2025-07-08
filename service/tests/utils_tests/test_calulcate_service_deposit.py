
from django.test import TestCase
from service.utils.calulcate_service_deposit import calculate_service_deposit
from service.tests.test_helpers.model_factories import TempServiceBookingFactory, ServiceSettingsFactory, ServiceTypeFactory
from decimal import Decimal
from service.models import ServiceSettings # Import ServiceSettings

class CalculateServiceDepositTest(TestCase):

    def test_no_service_settings(self):
        ServiceSettings.objects.all().delete()
        temp_booking = TempServiceBookingFactory()
        deposit = calculate_service_deposit(temp_booking)
        self.assertEqual(deposit, Decimal('0.00'))

    def test_online_deposit_disabled(self):
        ServiceSettingsFactory(enable_online_deposit=False)
        temp_booking = TempServiceBookingFactory()
        deposit = calculate_service_deposit(temp_booking)
        self.assertEqual(deposit, Decimal('0.00'))

    def test_flat_fee_deposit_method(self):
        ServiceSettingsFactory(enable_online_deposit=True, deposit_calc_method='FLAT_FEE', deposit_flat_fee_amount=Decimal('50.00'))
        service_type = ServiceTypeFactory(base_price=Decimal('150.00'))
        temp_booking = TempServiceBookingFactory(service_type=service_type)
        deposit = calculate_service_deposit(temp_booking)
        self.assertEqual(deposit, Decimal('50.00'))

    def test_percentage_deposit_method(self):
        ServiceSettingsFactory(enable_online_deposit=True, deposit_calc_method='PERCENTAGE', deposit_percentage=Decimal('0.10'))
        service_type = ServiceTypeFactory(base_price=Decimal('200.00'))
        temp_booking = TempServiceBookingFactory(service_type=service_type)
        deposit = calculate_service_deposit(temp_booking)
        self.assertEqual(deposit, Decimal('20.00'))

    def test_percentage_deposit_method_zero_total(self):
        ServiceSettingsFactory(enable_online_deposit=True, deposit_calc_method='PERCENTAGE', deposit_percentage=Decimal('0.10'))
        service_type = ServiceTypeFactory(base_price=Decimal('0.00'))
        temp_booking = TempServiceBookingFactory(service_type=service_type)
        deposit = calculate_service_deposit(temp_booking)
        self.assertEqual(deposit, Decimal('0.00'))
