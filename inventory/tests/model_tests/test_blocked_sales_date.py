from django.test import TestCase
from django.core.exceptions import ValidationError
from datetime import date

                                                          
from inventory.models import BlockedSalesDate

                                                                                            
from ..test_helpers.model_factories import BlockedSalesDateFactory


class BlockedSalesDateModelTest(TestCase):
    #--

    @classmethod
    def setUpTestData(cls):
        #--
                                                                                             
        BlockedSalesDate.objects.all().delete()

        cls.blocked_date_range = BlockedSalesDateFactory()
        cls.blocked_single_day = BlockedSalesDateFactory(
            start_date=date(2025, 1, 15),
            end_date=date(2025, 1, 15),
            description="Public Holiday"
        )

    def test_blocked_sales_date_creation(self):
        #--
        self.assertIsInstance(self.blocked_date_range, BlockedSalesDate)
        self.assertIsNotNone(self.blocked_date_range.pk)                                              

        self.assertIsInstance(self.blocked_single_day, BlockedSalesDate)
        self.assertIsNotNone(self.blocked_single_day.pk)

    def test_start_date_field(self):
        #--
        blocked_date = self.blocked_date_range
        self.assertIsInstance(blocked_date.start_date, date)
        self.assertIsNotNone(blocked_date.start_date)
        self.assertEqual(
            blocked_date._meta.get_field('start_date').help_text,
            "The start date of the blocked period for sales appointments."
        )

    def test_end_date_field(self):
        #--
        blocked_date = self.blocked_date_range
        self.assertIsInstance(blocked_date.end_date, date)
        self.assertIsNotNone(blocked_date.end_date)
        self.assertEqual(
            blocked_date._meta.get_field('end_date').help_text,
            "The end date of the blocked period (inclusive) for sales appointments."
        )

    def test_description_field(self):
        #--
        blocked_date = self.blocked_date_range
        self.assertEqual(blocked_date._meta.get_field('description').max_length, 255)
        self.assertTrue(blocked_date._meta.get_field('description').blank)
        self.assertTrue(blocked_date._meta.get_field('description').null)
        self.assertIsInstance(blocked_date.description, (str, type(None)))

                                 
        self.assertEqual(self.blocked_single_day.description, "Public Holiday")
        
                                                                     
        no_desc_block = BlockedSalesDate.objects.create(
            start_date=date(2025, 2, 1),
            end_date=date(2025, 2, 1),
            description=None
        )
        self.assertIsNone(no_desc_block.description)


    def test_str_method_single_day(self):
        #--
                                                                                
        expected_str = f"Blocked Sales Date: {self.blocked_single_day.start_date.strftime('%Y-%m-%d')}"
        self.assertEqual(str(self.blocked_single_day), expected_str)

    def test_str_method_date_range(self):
        #--
        start = date(2025, 3, 1)
        end = date(2025, 3, 5)
        blocked_range = BlockedSalesDateFactory(start_date=start, end_date=end)
                                                                                               
        expected_str = f"Blocked Sales Dates: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}"
        self.assertEqual(str(blocked_range), expected_str)

    def test_ordering_meta(self):
        #--
                                                                
        BlockedSalesDate.objects.all().delete()

                                                    
        b1 = BlockedSalesDate.objects.create(start_date=date(2025, 1, 5), end_date=date(2025, 1, 5))
        b2 = BlockedSalesDate.objects.create(start_date=date(2025, 1, 1), end_date=date(2025, 1, 1))
        b3 = BlockedSalesDate.objects.create(start_date=date(2025, 1, 10), end_date=date(2025, 1, 10))

                                   
        ordered_dates = BlockedSalesDate.objects.all()
        self.assertEqual(list(ordered_dates), [b2, b1, b3])

                                         
        self.assertEqual(BlockedSalesDate._meta.ordering, ['start_date'])


    def test_verbose_names_meta(self):
        #--
        self.assertEqual(BlockedSalesDate._meta.verbose_name, "Blocked Sales Date")
        self.assertEqual(BlockedSalesDate._meta.verbose_name_plural, "Blocked Sales Dates")

    def test_end_date_not_before_start_date_validation(self):
        #--
                                                                              
        expected_error_message = "End date cannot be before the start date."
        with self.assertRaisesMessage(ValidationError, expected_error_message) as cm:
            blocked_date = BlockedSalesDate(
                start_date=date(2025, 1, 10),
                end_date=date(2025, 1, 5),
                description="Invalid Range"
            )
            blocked_date.full_clean()                                              

                                                             
        self.assertIn('end_date', cm.exception.message_dict)
        self.assertEqual(cm.exception.message_dict['end_date'][0], expected_error_message)

                                                      
        valid_block_equal = BlockedSalesDate(
            start_date=date(2025, 4, 1),
            end_date=date(2025, 4, 1)
        )
        try:
            valid_block_equal.full_clean()
        except ValidationError:
            self.fail("ValidationError raised for valid equal start_date and end_date.")

                                                     
        valid_block_after = BlockedSalesDate(
            start_date=date(2025, 4, 1),
            end_date=date(2025, 4, 5)
        )
        try:
            valid_block_after.full_clean()
        except ValidationError:
            self.fail("ValidationError raised for valid end_date after start_date.")

