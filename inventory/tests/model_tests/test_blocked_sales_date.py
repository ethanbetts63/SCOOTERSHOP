from django.test import TestCase
from django.core.exceptions import ValidationError
from datetime import date

# Import the BlockedSalesDate model from the inventory app
from inventory.models import BlockedSalesDate

# Import the BlockedSalesDateFactory from your inventory's test_helpers.model_factories file
from ..test_helpers.model_factories import BlockedSalesDateFactory


class BlockedSalesDateModelTest(TestCase):
    """
    Tests for the BlockedSalesDate model in the inventory app.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods for BlockedSalesDate.
        """
        # Ensure the database is clean before creating test data for this specific test class
        BlockedSalesDate.objects.all().delete()

        cls.blocked_date_range = BlockedSalesDateFactory()
        cls.blocked_single_day = BlockedSalesDateFactory(
            start_date=date(2025, 1, 15),
            end_date=date(2025, 1, 15),
            description="Public Holiday"
        )

    def test_blocked_sales_date_creation(self):
        """
        Test that a BlockedSalesDate instance can be created successfully using the factory.
        """
        self.assertIsInstance(self.blocked_date_range, BlockedSalesDate)
        self.assertIsNotNone(self.blocked_date_range.pk) # Check if it has a primary key (saved to DB)

        self.assertIsInstance(self.blocked_single_day, BlockedSalesDate)
        self.assertIsNotNone(self.blocked_single_day.pk)

    def test_start_date_field(self):
        """
        Test the 'start_date' field properties of BlockedSalesDate.
        """
        blocked_date = self.blocked_date_range
        self.assertIsInstance(blocked_date.start_date, date)
        self.assertIsNotNone(blocked_date.start_date)
        self.assertEqual(
            blocked_date._meta.get_field('start_date').help_text,
            "The start date of the blocked period for sales appointments."
        )

    def test_end_date_field(self):
        """
        Test the 'end_date' field properties of BlockedSalesDate.
        """
        blocked_date = self.blocked_date_range
        self.assertIsInstance(blocked_date.end_date, date)
        self.assertIsNotNone(blocked_date.end_date)
        self.assertEqual(
            blocked_date._meta.get_field('end_date').help_text,
            "The end date of the blocked period (inclusive) for sales appointments."
        )

    def test_description_field(self):
        """
        Test the 'description' field properties of BlockedSalesDate.
        """
        blocked_date = self.blocked_date_range
        self.assertEqual(blocked_date._meta.get_field('description').max_length, 255)
        self.assertTrue(blocked_date._meta.get_field('description').blank)
        self.assertTrue(blocked_date._meta.get_field('description').null)
        self.assertIsInstance(blocked_date.description, (str, type(None)))

        # Test with a description
        self.assertEqual(self.blocked_single_day.description, "Public Holiday")
        
        # Test with no description (create explicitly to ensure None)
        no_desc_block = BlockedSalesDate.objects.create(
            start_date=date(2025, 2, 1),
            end_date=date(2025, 2, 1),
            description=None
        )
        self.assertIsNone(no_desc_block.description)


    def test_str_method_single_day(self):
        """
        Test the __str__ method for a single blocked sales date.
        """
        # The __str__ method should now reflect "Blocked Sales Date: YYYY-MM-DD"
        expected_str = f"Blocked Sales Date: {self.blocked_single_day.start_date.strftime('%Y-%m-%d')}"
        self.assertEqual(str(self.blocked_single_day), expected_str)

    def test_str_method_date_range(self):
        """
        Test the __str__ method for a blocked sales date range.
        """
        start = date(2025, 3, 1)
        end = date(2025, 3, 5)
        blocked_range = BlockedSalesDateFactory(start_date=start, end_date=end)
        # The __str__ method should now reflect "Blocked Sales Dates: YYYY-MM-DD to YYYY-MM-DD"
        expected_str = f"Blocked Sales Dates: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}"
        self.assertEqual(str(blocked_range), expected_str)

    def test_ordering_meta(self):
        """
        Test the Meta 'ordering' option for BlockedSalesDate.
        """
        # Clear existing data to ensure a clean test of ordering
        BlockedSalesDate.objects.all().delete()

        # Create dates out of order to test ordering
        b1 = BlockedSalesDate.objects.create(start_date=date(2025, 1, 5), end_date=date(2025, 1, 5))
        b2 = BlockedSalesDate.objects.create(start_date=date(2025, 1, 1), end_date=date(2025, 1, 1))
        b3 = BlockedSalesDate.objects.create(start_date=date(2025, 1, 10), end_date=date(2025, 1, 10))

        # Fetch all and check order
        ordered_dates = BlockedSalesDate.objects.all()
        self.assertEqual(list(ordered_dates), [b2, b1, b3])

        # Verify the meta option directly
        self.assertEqual(BlockedSalesDate._meta.ordering, ['start_date'])


    def test_verbose_names_meta(self):
        """
        Test the Meta 'verbose_name' and 'verbose_name_plural' options for BlockedSalesDate.
        """
        self.assertEqual(BlockedSalesDate._meta.verbose_name, "Blocked Sales Date")
        self.assertEqual(BlockedSalesDate._meta.verbose_name_plural, "Blocked Sales Dates")

    def test_end_date_not_before_start_date_validation(self):
        """
        Test that end_date cannot be before start_date in BlockedSalesDate,
        using the model's clean method.
        """
        # Attempt to create a blocked date where end_date is before start_date
        expected_error_message = "End date cannot be before the start date."
        with self.assertRaisesMessage(ValidationError, expected_error_message) as cm:
            blocked_date = BlockedSalesDate(
                start_date=date(2025, 1, 10),
                end_date=date(2025, 1, 5),
                description="Invalid Range"
            )
            blocked_date.full_clean() # Call full_clean to trigger model validation

        # Check that the error is specifically for 'end_date'
        self.assertIn('end_date', cm.exception.message_dict)
        self.assertEqual(cm.exception.message_dict['end_date'][0], expected_error_message)

        # Test valid case (end_date equals start_date)
        valid_block_equal = BlockedSalesDate(
            start_date=date(2025, 4, 1),
            end_date=date(2025, 4, 1)
        )
        try:
            valid_block_equal.full_clean()
        except ValidationError:
            self.fail("ValidationError raised for valid equal start_date and end_date.")

        # Test valid case (end_date after start_date)
        valid_block_after = BlockedSalesDate(
            start_date=date(2025, 4, 1),
            end_date=date(2025, 4, 5)
        )
        try:
            valid_block_after.full_clean()
        except ValidationError:
            self.fail("ValidationError raised for valid end_date after start_date.")

