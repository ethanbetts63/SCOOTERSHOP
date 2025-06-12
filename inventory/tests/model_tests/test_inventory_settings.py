from django.test import TestCase
from django.core.exceptions import ValidationError
from datetime import time, date
from decimal import Decimal
import datetime
# Import the InventorySettings model
from inventory.models import InventorySettings

# Import the InventorySettingsFactory from your factories file
from ..test_helpers.model_factories import InventorySettingsFactory


class InventorySettingsModelTest(TestCase):
    """
    Tests for the InventorySettings model, which is designed as a singleton.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up the single instance of InventorySettings used by all test methods.
        """
        # Ensure the database is clean before creating test data for this specific test class
        InventorySettings.objects.all().delete()

        # Create the single instance of InventorySettings using the factory
        cls.settings = InventorySettingsFactory()

    def test_inventory_settings_creation(self):
        """
        Test that an InventorySettings instance can be created successfully using the factory
        and that it is indeed a singleton (only one exists).
        """
        self.assertIsInstance(self.settings, InventorySettings)
        self.assertIsNotNone(self.settings.pk) # Check if it has a primary key (saved to DB)

        # Verify that only one instance exists in the database
        self.assertEqual(InventorySettings.objects.count(), 1)

        # IMPORTANT CORRECTION:
        # Attempt to create a *new* instance directly (without a pk) and save it.
        # This should correctly trigger the ValidationError in the model's save method.
        with self.assertRaisesMessage(ValidationError, "Only one instance of InventorySettings can be created. Please edit the existing one."):
            new_settings_attempt = InventorySettings()
            new_settings_attempt.save() # This call should raise the ValidationError

    def test_enable_sales_system_field(self):
        """
        Test the 'enable_sales_system' field properties.
        """
        field = self.settings._meta.get_field('enable_sales_system')
        self.assertIsInstance(self.settings.enable_sales_system, bool)
        self.assertTrue(field.default)
        self.assertEqual(field.help_text, "Globally enable or disable the sales booking and enquiry system.")

    def test_enable_depositless_enquiry_field(self):
        """
        Test the 'enable_depositless_enquiry' field properties.
        """
        field = self.settings._meta.get_field('enable_depositless_enquiry')
        self.assertIsInstance(self.settings.enable_depositless_enquiry, bool)
        self.assertTrue(field.default)
        self.assertEqual(field.help_text, "Allow customers to submit an enquiry for a motorcycle without requiring a deposit.")

    def test_enable_reservation_by_deposit_field(self):
        """
        Test the 'enable_reservation_by_deposit' field properties.
        """
        field = self.settings._meta.get_field('enable_reservation_by_deposit')
        self.assertIsInstance(self.settings.enable_reservation_by_deposit, bool)
        self.assertTrue(field.default)
        self.assertEqual(field.help_text, "Allow customers to reserve a motorcycle by paying a deposit.")

    def test_deposit_amount_field(self):
        """
        Test the 'deposit_amount' field properties.
        """
        field = self.settings._meta.get_field('deposit_amount')
        self.assertIsInstance(self.settings.deposit_amount, Decimal)
        self.assertEqual(field.max_digits, 10)
        self.assertEqual(field.decimal_places, 2)
        self.assertEqual(field.default, Decimal('100.00'))
        self.assertEqual(field.help_text, "The fixed amount required for a motorcycle reservation deposit.")

        # Test validation: negative deposit amount
        # Retrieve the instance to modify, ensure it's not the class-level 'settings' to avoid conflicts
        settings_invalid = InventorySettings.objects.get(pk=self.settings.pk)
        settings_invalid.deposit_amount = Decimal('-50.00')
        with self.assertRaisesMessage(ValidationError, "Deposit amount cannot be negative.") as cm:
            settings_invalid.full_clean()
        self.assertIn('deposit_amount', cm.exception.message_dict)

    def test_deposit_lifespan_days_field(self):
        """
        Test the 'deposit_lifespan_days' field properties.
        """
        field = self.settings._meta.get_field('deposit_lifespan_days')
        self.assertIsInstance(self.settings.deposit_lifespan_days, int)
        self.assertEqual(field.default, 5)
        self.assertEqual(field.help_text, "Number of days a deposit holds a motorcycle reservation. After this period, the reservation may expire.")

        # Test validation: negative deposit lifespan days
        settings_invalid = InventorySettings.objects.get(pk=self.settings.pk)
        settings_invalid.deposit_lifespan_days = -1
        with self.assertRaisesMessage(ValidationError, "Deposit lifespan days cannot be negative.") as cm:
            settings_invalid.full_clean()
        self.assertIn('deposit_lifespan_days', cm.exception.message_dict)

    def test_auto_refund_expired_deposits_field(self):
        """
        Test the 'auto_refund_expired_deposits' field properties.
        """
        field = self.settings._meta.get_field('auto_refund_expired_deposits')
        self.assertIsInstance(self.settings.auto_refund_expired_deposits, bool)
        self.assertTrue(field.default)
        self.assertEqual(field.help_text, "Automatically process a full refund for deposits if the reservation expires without confirmation/completion.")

    def test_sales_booking_open_days_field(self):
        """
        Test the 'sales_booking_open_days' field properties.
        """
        field = self.settings._meta.get_field('sales_booking_open_days')
        self.assertIsInstance(self.settings.sales_booking_open_days, str)
        self.assertEqual(field.max_length, 255)
        self.assertEqual(field.default, "Mon,Tue,Wed,Thu,Fri,Sat")
        self.assertEqual(field.help_text, "Comma-separated list of days when sales appointments (test drives, viewings) are open.")

    def test_sales_appointment_time_fields(self):
        """
        Test 'sales_appointment_start_time' and 'sales_appointment_end_time' properties and validation.
        """
        start_field = self.settings._meta.get_field('sales_appointment_start_time')
        end_field = self.settings._meta.get_field('sales_appointment_end_time')

        self.assertIsInstance(self.settings.sales_appointment_start_time, time)
        self.assertIsInstance(self.settings.sales_appointment_end_time, time)
        self.assertEqual(start_field.default, time(9, 0))
        self.assertEqual(end_field.default, time(17, 0))
        self.assertEqual(start_field.help_text, "The earliest time a sales appointment can be scheduled.")
        self.assertEqual(end_field.help_text, "The latest time a sales appointment can be scheduled.")

        # Test validation: start_time >= end_time
        settings_invalid = InventorySettings.objects.get(pk=self.settings.pk)
        settings_invalid.sales_appointment_start_time = time(10, 0)
        settings_invalid.sales_appointment_end_time = time(9, 0)
        with self.assertRaisesMessage(ValidationError, "Start time must be earlier than end time.") as cm:
            settings_invalid.full_clean()
        self.assertIn('sales_appointment_start_time', cm.exception.message_dict)
        self.assertIn('sales_appointment_end_time', cm.exception.message_dict)

        # Test validation: start_time == end_time
        settings_invalid = InventorySettings.objects.get(pk=self.settings.pk)
        settings_invalid.sales_appointment_start_time = time(10, 0)
        settings_invalid.sales_appointment_end_time = time(10, 0)
        with self.assertRaisesMessage(ValidationError, "Start time must be earlier than end time.") as cm:
            settings_invalid.full_clean()
        self.assertIn('sales_appointment_start_time', cm.exception.message_dict)
        self.assertIn('sales_appointment_end_time', cm.exception.message_dict)

    def test_sales_appointment_spacing_mins_field(self):
        """
        Test the 'sales_appointment_spacing_mins' field properties and validation.
        """
        field = self.settings._meta.get_field('sales_appointment_spacing_mins')
        self.assertIsInstance(self.settings.sales_appointment_spacing_mins, int)
        self.assertEqual(field.default, 30)
        self.assertEqual(field.help_text, "The minimum interval in minutes between two sales appointments on the same day.")

        # Test validation: non-positive spacing
        settings_invalid = InventorySettings.objects.get(pk=self.settings.pk)
        settings_invalid.sales_appointment_spacing_mins = 0
        with self.assertRaisesMessage(ValidationError, "Appointment spacing must be a positive integer.") as cm:
            settings_invalid.full_clean()
        self.assertIn('sales_appointment_spacing_mins', cm.exception.message_dict)

        settings_invalid = InventorySettings.objects.get(pk=self.settings.pk) # Re-fetch to reset
        settings_invalid.sales_appointment_spacing_mins = -10
        with self.assertRaisesMessage(ValidationError, "Appointment spacing must be a positive integer.") as cm:
            settings_invalid.full_clean()
        self.assertIn('sales_appointment_spacing_mins', cm.exception.message_dict)


    def test_max_advance_booking_days_field(self):
        """
        Test the 'max_advance_booking_days' field properties and validation.
        """
        field = self.settings._meta.get_field('max_advance_booking_days')
        self.assertIsInstance(self.settings.max_advance_booking_days, int)
        self.assertEqual(field.default, 90)
        self.assertEqual(field.help_text, "Maximum number of days in advance a customer can book a sales appointment.")

        # Test validation: negative max advance booking days
        settings_invalid = InventorySettings.objects.get(pk=self.settings.pk)
        settings_invalid.max_advance_booking_days = -5
        with self.assertRaisesMessage(ValidationError, "Maximum advance booking days cannot be negative.") as cm:
            settings_invalid.full_clean()
        self.assertIn('max_advance_booking_days', cm.exception.message_dict)

    def test_min_advance_booking_hours_field(self):
        """
        Test the 'min_advance_booking_hours' field properties and validation.
        """
        field = self.settings._meta.get_field('min_advance_booking_hours')
        self.assertIsInstance(self.settings.min_advance_booking_hours, int)
        self.assertEqual(field.default, 24)
        self.assertEqual(field.help_text, "Minimum number of hours notice required for a sales appointment.")

        # Test validation: negative min advance booking hours
        settings_invalid = InventorySettings.objects.get(pk=self.settings.pk)
        settings_invalid.min_advance_booking_hours = -1
        with self.assertRaisesMessage(ValidationError, "Minimum advance booking hours cannot be negative.") as cm:
            settings_invalid.full_clean()
        self.assertIn('min_advance_booking_hours', cm.exception.message_dict)

    def test_currency_fields(self):
        """
        Test 'currency_code' and 'currency_symbol' fields.
        """
        code_field = self.settings._meta.get_field('currency_code')
        symbol_field = self.settings._meta.get_field('currency_symbol')

        self.assertIsInstance(self.settings.currency_code, str)
        self.assertIsInstance(self.settings.currency_symbol, str)
        self.assertEqual(code_field.max_length, 3)
        self.assertEqual(symbol_field.max_length, 5)
        self.assertEqual(code_field.default, 'AUD')
        self.assertEqual(symbol_field.default, '$')
        self.assertEqual(code_field.help_text, "The three-letter ISO currency code for sales transactions (e.g., AUD, USD).")
        self.assertEqual(symbol_field.help_text, "The currency symbol for sales transactions (e.g., $).")

    def test_terms_and_conditions_text_field(self):
        """
        Test the 'terms_and_conditions_text' field properties.
        """
        field = self.settings._meta.get_field('terms_and_conditions_text')
        self.assertIsInstance(self.settings.terms_and_conditions_text, (str, type(None)))
        self.assertTrue(field.blank)
        self.assertTrue(field.null)
        self.assertEqual(field.help_text, "Custom terms and conditions text displayed during the sales/reservation process.")

    def test_timestamps(self):
        """
        Test 'created_at' and 'updated_at' fields.
        """
        self.assertIsNotNone(self.settings.created_at)
        self.assertIsNotNone(self.settings.updated_at)
        self.assertIsInstance(self.settings.created_at, datetime.datetime)
        self.assertIsInstance(self.settings.updated_at, datetime.datetime)

    def test_str_method(self):
        """
        Test the __str__ method of InventorySettings.
        """
        self.assertEqual(str(self.settings), "Inventory Settings")

    def test_verbose_names_meta(self):
        """
        Test the Meta 'verbose_name' and 'verbose_name_plural' options.
        """
        self.assertEqual(InventorySettings._meta.verbose_name, "Inventory Settings")
        self.assertEqual(InventorySettings._meta.verbose_name_plural, "Inventory Settings")

    def test_enable_sales_new_bikes_field(self):
        """
        Test the 'enable_sales_new_bikes' field properties.
        """
        field = self.settings._meta.get_field('enable_sales_new_bikes')
        self.assertIsInstance(self.settings.enable_sales_new_bikes, bool)
        self.assertTrue(field.default)
        self.assertEqual(field.help_text, "Enable the sales process for 'New' motorcycles in the inventory.")

    def test_enable_sales_used_bikes_field(self):
        """
        Test the 'enable_sales_used_bikes' field properties.
        """
        field = self.settings._meta.get_field('enable_sales_used_bikes')
        self.assertIsInstance(self.settings.enable_sales_used_bikes, bool)
        self.assertTrue(field.default)
        self.assertEqual(field.help_text, "Enable the sales process for 'Used' and 'Demo' motorcycles in the inventory.")

    def test_require_drivers_license_field(self):
        """
        Test the 'require_drivers_license' field properties.
        """
        field = self.settings._meta.get_field('require_drivers_license')
        self.assertIsInstance(self.settings.require_drivers_license, bool)
        self.assertFalse(field.default) # Default is False
        self.assertEqual(field.help_text, "Require customers to provide driver's license details.")

    def test_require_address_info_field(self):
        """
        Test the 'require_address_info' field properties.
        """
        field = self.settings._meta.get_field('require_address_info')
        self.assertIsInstance(self.settings.require_address_info, bool)
        self.assertFalse(field.default) # Default is False
        self.assertEqual(field.help_text, "Require customers to provide address details.")

