from django.test import TestCase
from service.utils.calculate_service_total import calculate_service_total
from service.tests.test_helpers.model_factories import TempServiceBookingFactory, ServiceTypeFactory
from decimal import Decimal

class CalculateServiceTotalTest(TestCase):

    def test_calculate_service_total(self):
        service_type = ServiceTypeFactory(base_price=Decimal('150.00'))
        temp_booking = TempServiceBookingFactory(service_type=service_type)
        total = calculate_service_total(temp_booking)
        self.assertEqual(total, Decimal('150.00'))

    def test_calculate_service_total_zero_price(self):
        service_type = ServiceTypeFactory(base_price=Decimal('0.00'))
        temp_booking = TempServiceBookingFactory(service_type=service_type)
        total = calculate_service_total(temp_booking)
        self.assertEqual(total, Decimal('0.00'))

    def test_calculate_service_total_no_service_type(self):
        temp_booking = TempServiceBookingFactory.build(service_type=None)
        total = calculate_service_total(temp_booking)
        self.assertEqual(total, Decimal('0.00'))