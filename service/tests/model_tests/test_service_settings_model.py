from django.test import TestCase
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import time
from faker import Faker

from service.models import ServiceSettings
from service.tests.test_helpers.model_factories import ServiceSettingsFactory

fake = Faker()

class ServiceSettingsModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # The factory handles the singleton nature of the settings model
        cls.settings = ServiceSettingsFactory()

    def test_service_settings_creation(self):
        self.assertIsNotNone(self.settings)
        self.assertIsInstance(self.settings, ServiceSettings)
        self.assertEqual(ServiceSettings.objects.count(), 1)

    def test_singleton_enforcement(self):
        with self.assertRaises(ValidationError) as cm:
            ServiceSettings(
                booking_advance_notice=3,
                daily_service_slots=5,
            ).save()
        self.assertIn("Only one instance of ServiceSettings can be created", str(cm.exception))
        self.assertEqual(ServiceSettings.objects.count(), 1)

    def test_str_method(self):
        self.assertEqual(str(self.settings), "Service Settings")

    def test_default_values(self):
        # The factory sets values, so let's delete and create a raw one to check defaults
        ServiceSettings.objects.all().delete()
        settings = ServiceSettings.objects.create()
        self.assertEqual(settings.booking_advance_notice, 2)
        self.assertEqual(settings.daily_service_slots, 8)
        self.assertEqual(settings.booking_open_days, "Mon,Tue,Wed,Thu,Fri")
        self.assertEqual(settings.drop_off_start_time, time(9, 0))
        self.assertEqual(settings.drop_off_end_time, time(17, 0))
        self.assertEqual(settings.drop_off_spacing_mins, 30)
        self.assertEqual(settings.max_advance_dropoff_days, 3)
        self.assertEqual(settings.latest_same_day_dropoff_time, time(12, 0))
        
        self.assertFalse(settings.enable_after_hours_dropoff)
        self.assertEqual(settings.deposit_calc_method, "FLAT_FEE")
        self.assertEqual(settings.deposit_flat_fee_amount, Decimal("50.00"))
        self.assertEqual(settings.deposit_percentage, Decimal("0.00"))
        self.assertFalse(settings.enable_online_full_payment)
        self.assertTrue(settings.enable_online_deposit)
        self.assertTrue(settings.enable_instore_full_payment)
        self.assertEqual(settings.currency_code, "AUD")
        self.assertEqual(settings.currency_symbol, "$")
        self.assertIsInstance(settings.enable_estimated_pickup_date, bool)

    def test_clean_method_daily_service_slots(self):
        settings = self.settings
        settings.daily_service_slots = 0
        with self.assertRaises(ValidationError) as cm:
            settings.full_clean()
        self.assertIn("daily_service_slots", cm.exception.message_dict)
        self.assertIn("Ensure this value is greater than or equal to 1.", cm.exception.message_dict["daily_service_slots"][0])

    def test_field_attributes(self):
        self.assertEqual(self.settings._meta.get_field("booking_open_days").max_length, 255)
        self.assertEqual(self.settings._meta.get_field("deposit_calc_method").max_length, 20)
        self.assertEqual(self.settings._meta.get_field("currency_code").max_length, 3)
        self.assertEqual(self.settings._meta.get_field("currency_symbol").max_length, 5)
        self.assertEqual(self.settings._meta.get_field("deposit_flat_fee_amount").max_digits, 10)
        self.assertEqual(self.settings._meta.get_field("deposit_flat_fee_amount").decimal_places, 2)
        self.assertEqual(self.settings._meta.get_field("deposit_percentage").max_digits, 5)
        self.assertEqual(self.settings._meta.get_field("deposit_percentage").decimal_places, 2)

    def test_clean_start_time_after_end_time(self):
        with self.assertRaises(ValidationError) as e:
            ServiceSettingsFactory(
                drop_off_start_time=time(18, 0),
                drop_off_end_time=time(9, 0)
            )
        self.assertIn("drop_off_start_time", e.exception.message_dict)
        self.assertIn("drop_off_end_time", e.exception.message_dict)

    def test_clean_invalid_drop_off_spacing(self):
        with self.assertRaises(ValidationError) as e:
            ServiceSettingsFactory(drop_off_spacing_mins=0)
        self.assertIn("drop_off_spacing_mins", e.exception.message_dict)

        with self.assertRaises(ValidationError) as e:
            ServiceSettingsFactory(drop_off_spacing_mins=61)
        self.assertIn("drop_off_spacing_mins", e.exception.message_dict)

    def test_clean_negative_max_advance_dropoff_days(self):
        with self.assertRaises(ValidationError) as e:
            ServiceSettingsFactory(max_advance_dropoff_days=-1)
        self.assertIn("max_advance_dropoff_days", e.exception.message_dict)

    def test_clean_invalid_latest_same_day_dropoff_time(self):
        # Before start time
        with self.assertRaises(ValidationError) as e:
            ServiceSettingsFactory(
                drop_off_start_time=time(9, 0),
                drop_off_end_time=time(17, 0),
                latest_same_day_dropoff_time=time(8, 0)
            )
        self.assertIn("latest_same_day_dropoff_time", e.exception.message_dict)

        # After end time
        with self.assertRaises(ValidationError) as e:
            ServiceSettingsFactory(
                drop_off_start_time=time(9, 0),
                drop_off_end_time=time(17, 0),
                latest_same_day_dropoff_time=time(18, 0)
            )
        self.assertIn("latest_same_day_dropoff_time", e.exception.message_dict)

    def test_clean_invalid_deposit_percentage(self):
        # Below 0
        with self.assertRaises(ValidationError) as e:
            ServiceSettingsFactory(deposit_percentage=Decimal("-0.01"))
        self.assertIn("deposit_percentage", e.exception.message_dict)

        # Above 100
        with self.assertRaises(ValidationError) as e:
            ServiceSettingsFactory(deposit_percentage=Decimal("100.01"))
        self.assertIn("deposit_percentage", e.exception.message_dict)

    def test_valid_settings_can_be_saved(self):
        settings = ServiceSettingsFactory(
            drop_off_start_time=time(9, 0),
            drop_off_end_time=time(17, 0),
            latest_same_day_dropoff_time=time(16, 0),
            deposit_percentage=Decimal("50.00")
        )
        settings.full_clean()
        settings.save()
        self.assertEqual(settings.latest_same_day_dropoff_time, time(16, 0))
        self.assertEqual(settings.deposit_percentage, Decimal("50.00"))
