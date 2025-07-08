from django.test import TestCase
from inventory.utils.get_sales_faqs import get_faqs_for_step
from inventory.tests.test_helpers.model_factories import SalesfaqFactory
from inventory.models import Salesfaq

class GetSalesFaqsTest(TestCase):

    def setUp(self):
        # Create some FAQs for testing
        self.faq_step1_1 = SalesfaqFactory(booking_step='step1', display_order=1, is_active=True)
        self.faq_step1_2 = SalesfaqFactory(booking_step='step1', display_order=2, is_active=True)
        self.faq_step2_1 = SalesfaqFactory(booking_step='step2', display_order=1, is_active=True)
        self.faq_general_1 = SalesfaqFactory(booking_step='general', display_order=1, is_active=True)
        self.faq_general_2 = SalesfaqFactory(booking_step='general', display_order=2, is_active=True)
        self.faq_inactive = SalesfaqFactory(booking_step='step1', display_order=3, is_active=False)

    def test_get_faqs_for_step_step1(self):
        faqs = get_faqs_for_step('step1')
        self.assertEqual(faqs.count(), 4) # 2 step1 + 2 general
        self.assertIn(self.faq_step1_1, faqs)
        self.assertIn(self.faq_step1_2, faqs)
        self.assertIn(self.faq_general_1, faqs)
        self.assertIn(self.faq_general_2, faqs)
        self.assertNotIn(self.faq_inactive, faqs)

        # Test ordering: general FAQs should come after step-specific FAQs due to '-booking_step'
        # and then by display_order
        expected_order = [
            self.faq_step1_1,
            self.faq_step1_2,
            self.faq_general_1,
            self.faq_general_2,
        ]
        self.assertListEqual(list(faqs), expected_order)

    def test_get_faqs_for_step_step2(self):
        faqs = get_faqs_for_step('step2')
        self.assertEqual(faqs.count(), 3) # 1 step2 + 2 general
        self.assertIn(self.faq_step2_1, faqs)
        self.assertIn(self.faq_general_1, faqs)
        self.assertIn(self.faq_general_2, faqs)
        self.assertNotIn(self.faq_inactive, faqs)

        expected_order = [
            self.faq_step2_1,
            self.faq_general_1,
            self.faq_general_2,
        ]
        self.assertListEqual(list(faqs), expected_order)

    def test_get_faqs_for_step_nonexistent_step(self):
        faqs = get_faqs_for_step('nonexistent')
        self.assertEqual(faqs.count(), 2) # Only general FAQs
        self.assertIn(self.faq_general_1, faqs)
        self.assertIn(self.faq_general_2, faqs)
        self.assertNotIn(self.faq_inactive, faqs)

        expected_order = [
            self.faq_general_1,
            self.faq_general_2,
        ]
        self.assertListEqual(list(faqs), expected_order)

    def test_inactive_faqs_not_returned(self):
        faqs = get_faqs_for_step('step1')
        self.assertNotIn(self.faq_inactive, faqs)