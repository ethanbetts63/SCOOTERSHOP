from django.test import TestCase
from inventory.forms import InventorySettingsForm
from datetime import time
from decimal import Decimal

class InventorySettingsFormTest(TestCase):

    def test_valid_form_data(self):
        form = InventorySettingsForm(data={
            'enable_depositless_viewing': True,
            'enable_reservation_by_deposit': True,
            'enable_sales_enquiries': True,
            'deposit_amount': Decimal('100.00'),
            'deposit_lifespan_days': 5,
            'enable_sales_new_bikes': True,
            'enable_sales_used_bikes': True,
            'require_drivers_license': False,
            'require_address_info': False,
            'sales_booking_open_days': 'Mon,Tue,Wed',
            'sales_appointment_start_time': time(9, 0),
            'sales_appointment_end_time': time(17, 0),
            'sales_appointment_spacing_mins': 30,
            'max_advance_booking_days': 90,
            'min_advance_booking_hours': 24,
            'send_sales_booking_to_mechanic_desk': True,
            'currency_code': 'AUD',
            'currency_symbol': '$',
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_negative_deposit_amount(self):
        form = InventorySettingsForm(data={
            'deposit_amount': Decimal('-10.00'),
            'deposit_lifespan_days': 5,
            'sales_appointment_start_time': time(9, 0),
            'sales_appointment_end_time': time(17, 0),
            'sales_appointment_spacing_mins': 30,
            'max_advance_booking_days': 90,
            'min_advance_booking_hours': 24,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('deposit_amount', form.errors)
        self.assertEqual(form.errors['deposit_amount'], ['Deposit amount cannot be negative.'])

    def test_negative_deposit_lifespan_days(self):
        form = InventorySettingsForm(data={
            'deposit_amount': Decimal('100.00'),
            'deposit_lifespan_days': -5,
            'sales_appointment_start_time': time(9, 0),
            'sales_appointment_end_time': time(17, 0),
            'sales_appointment_spacing_mins': 30,
            'max_advance_booking_days': 90,
            'min_advance_booking_hours': 24,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('deposit_lifespan_days', form.errors)
        self.assertEqual(form.errors['deposit_lifespan_days'], ['Deposit lifespan days cannot be negative.'])

    def test_start_time_after_end_time(self):
        form = InventorySettingsForm(data={
            'deposit_amount': Decimal('100.00'),
            'deposit_lifespan_days': 5,
            'sales_appointment_start_time': time(17, 0),
            'sales_appointment_end_time': time(9, 0),
            'sales_appointment_spacing_mins': 30,
            'max_advance_booking_days': 90,
            'min_advance_booking_hours': 24,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('sales_appointment_start_time', form.errors)
        self.assertIn('sales_appointment_end_time', form.errors)
        self.assertEqual(form.errors['sales_appointment_start_time'], ['Appointment start time must be earlier than end time.'])
        self.assertEqual(form.errors['sales_appointment_end_time'], ['Appointment end time must be later than start time.'])

    def test_non_positive_appointment_spacing(self):
        form = InventorySettingsForm(data={
            'deposit_amount': Decimal('100.00'),
            'deposit_lifespan_days': 5,
            'sales_appointment_start_time': time(9, 0),
            'sales_appointment_end_time': time(17, 0),
            'sales_appointment_spacing_mins': 0,
            'max_advance_booking_days': 90,
            'min_advance_booking_hours': 24,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('sales_appointment_spacing_mins', form.errors)
        self.assertEqual(form.errors['sales_appointment_spacing_mins'], ['Appointment spacing must be a positive integer.'])

    def test_negative_max_advance_booking_days(self):
        form = InventorySettingsForm(data={
            'deposit_amount': Decimal('100.00'),
            'deposit_lifespan_days': 5,
            'sales_appointment_start_time': time(9, 0),
            'sales_appointment_end_time': time(17, 0),
            'sales_appointment_spacing_mins': 30,
            'max_advance_booking_days': -10,
            'min_advance_booking_hours': 24,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('max_advance_booking_days', form.errors)
        self.assertEqual(form.errors['max_advance_booking_days'], ['Maximum advance booking days cannot be negative.'])

    def test_negative_min_advance_booking_hours(self):
        form = InventorySettingsForm(data={
            'deposit_amount': Decimal('100.00'),
            'deposit_lifespan_days': 5,
            'sales_appointment_start_time': time(9, 0),
            'sales_appointment_end_time': time(17, 0),
            'sales_appointment_spacing_mins': 30,
            'max_advance_booking_days': 90,
            'min_advance_booking_hours': -5,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('min_advance_booking_hours', form.errors)
        self.assertEqual(form.errors['min_advance_booking_hours'], ['Minimum advance booking hours cannot be negative.'])