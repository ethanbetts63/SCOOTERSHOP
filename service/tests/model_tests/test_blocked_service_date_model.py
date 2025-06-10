from django.test import TestCase
from django.core.exceptions import ValidationError
from datetime import date

# Import the BlockedServiceDate model
from service.models import BlockedServiceDate

# Import the BlockedServiceDateFactory from your factories file
from ..test_helpers.model_factories import BlockedServiceDateFactory

class BlockedServiceDateModelTest(TestCase):
    """
    Tests for the BlockedServiceDate model.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods.
        We'll create a single BlockedServiceDate instance using the factory.
        """
        # Ensure the database is clean before creating test data for this specific test class
        # (though Django's TestCase handles this, explicit clear can help in debugging)
        BlockedServiceDate.objects.all().delete()

        cls.blocked_date_range = BlockedServiceDateFactory()
        cls.blocked_single_day = BlockedServiceDateFactory(
            start_date=date(2025, 1, 15),
            end_date=date(2025, 1, 15),
            description="Public Holiday"
        )

    def test_blocked_service_date_creation(self):
        """
        Test that a BlockedServiceDate instance can be created successfully using the factory.
        """
        self.assertIsInstance(self.blocked_date_range, BlockedServiceDate)
        self.assertIsNotNone(self.blocked_date_range.pk) # Check if it has a primary key (saved to DB)

        self.assertIsInstance(self.blocked_single_day, BlockedServiceDate)
        self.assertIsNotNone(self.blocked_single_day.pk)

    def test_start_date_field(self):
        """
        Test the 'start_date' field properties.
        """
        blocked_date = self.blocked_date_range
        self.assertIsInstance(blocked_date.start_date, date)
        self.assertIsNotNone(blocked_date.start_date)
        self.assertEqual(blocked_date._meta.get_field('start_date').help_text, "The start date of the blocked period.")

    def test_end_date_field(self):
        """
        Test the 'end_date' field properties.
        """
        blocked_date = self.blocked_date_range
        self.assertIsInstance(blocked_date.end_date, date)
        self.assertIsNotNone(blocked_date.end_date)
        self.assertEqual(blocked_date._meta.get_field('end_date').help_text, "The end date of the blocked period (inclusive).")

    def test_description_field(self):
        """
        Test the 'description' field properties.
        """
        blocked_date = self.blocked_date_range
        self.assertEqual(blocked_date._meta.get_field('description').max_length, 255)
        self.assertTrue(blocked_date._meta.get_field('description').blank)
        self.assertTrue(blocked_date._meta.get_field('description').null)
        self.assertIsInstance(blocked_date.description, (str, type(None)))

        # Test with a description
        self.assertEqual(self.blocked_single_day.description, "Public Holiday")
        # Test with no description (should be None from factory default)
        # Factory generates a sentence by default, so to test actual None, create explicitly:
        no_desc_block = BlockedServiceDate.objects.create(
            start_date=date(2025, 2, 1),
            end_date=date(2025, 2, 1),
            description=None
        )
        self.assertIsNone(no_desc_block.description)


    def test_str_method_single_day(self):
        """
        Test the __str__ method for a single blocked day.
        """
        self.assertEqual(str(self.blocked_single_day), "Blocked: 2025-01-15")

    def test_str_method_date_range(self):
        """
        Test the __str__ method for a blocked date range.
        """
        # Ensure the factory creates a range for this test
        start = date(2025, 3, 1)
        end = date(2025, 3, 5)
        blocked_range = BlockedServiceDateFactory(start_date=start, end_date=end)
        self.assertEqual(str(blocked_range), "Blocked: 2025-03-01 to 2025-03-05")

    def test_ordering_meta(self):
        """
        Test the Meta 'ordering' option.
        """
        # Clear existing data to ensure a clean test of ordering
        BlockedServiceDate.objects.all().delete()

        # Create dates out of order to test ordering (removed 'name' argument)
        b1 = BlockedServiceDate.objects.create(start_date=date(2025, 1, 5), end_date=date(2025, 1, 5))
        b2 = BlockedServiceDate.objects.create(start_date=date(2025, 1, 1), end_date=date(2025, 1, 1))
        b3 = BlockedServiceDate.objects.create(start_date=date(2025, 1, 10), end_date=date(2025, 1, 10))

        # Fetch all and check order
        ordered_dates = BlockedServiceDate.objects.all()
        self.assertEqual(list(ordered_dates), [b2, b1, b3])

        # Verify the meta option directly
        self.assertEqual(BlockedServiceDate._meta.ordering, ['start_date'])


    def test_verbose_names_meta(self):
        """
        Test the Meta 'verbose_name' and 'verbose_name_plural' options.
        """
        self.assertEqual(BlockedServiceDate._meta.verbose_name, "Blocked Service Date")
        self.assertEqual(BlockedServiceDate._meta.verbose_name_plural, "Blocked Service Dates")

    def test_end_date_not_before_start_date_validation(self):
        """
        Test that end_date cannot be before start_date, using the model's clean method.
        """
        # Attempt to create a blocked date where end_date is before start_date
        expected_error_message = "End date cannot be before the start date."
        with self.assertRaisesMessage(ValidationError, expected_error_message) as cm:
            blocked_date = BlockedServiceDate(
                start_date=date(2025, 1, 10),
                end_date=date(2025, 1, 5),
                description="Invalid Range"
            )
            blocked_date.full_clean() # Call full_clean to trigger model validation

        # Check that the error is specifically for 'end_date'
        self.assertIn('end_date', cm.exception.message_dict)
        self.assertEqual(cm.exception.message_dict['end_date'][0], expected_error_message)

        # Test valid case (end_date equals start_date)
        valid_block_equal = BlockedServiceDate(
            start_date=date(2025, 4, 1),
            end_date=date(2025, 4, 1)
        )
        try:
            valid_block_equal.full_clean()
        except ValidationError:
            self.fail("ValidationError raised for valid equal start_date and end_date.")

        # Test valid case (end_date after start_date)
        valid_block_after = BlockedServiceDate(
            start_date=date(2025, 4, 1),
            end_date=date(2025, 4, 5)
        )
        try:
            valid_block_after.full_clean()
        except ValidationError:
            self.fail("ValidationError raised for valid end_date after start_date.")
