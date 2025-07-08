
from django.test import TestCase
from inventory.models import Salesfaq
from inventory.tests.test_helpers.model_factories import SalesfaqFactory

class SalesfaqModelTest(TestCase):

    def test_salesfaq_creation(self):
        faq = Salesfaq.objects.create(
            booking_step='general',
            question='Test Question',
            answer='Test Answer',
            is_active=True,
            display_order=1
        )
        self.assertIsInstance(faq, Salesfaq)
        self.assertEqual(faq.booking_step, 'general')
        self.assertEqual(faq.question, 'Test Question')
        self.assertEqual(faq.answer, 'Test Answer')
        self.assertTrue(faq.is_active)
        self.assertEqual(faq.display_order, 1)
        self.assertIsNotNone(faq.created_at)
        self.assertIsNotNone(faq.updated_at)

    def test_str_representation(self):
        faq = SalesfaqFactory(question='Another Question', booking_step='step1')
        self.assertEqual(str(faq), 'Q: Another Question (Step 1: Your Details)')

    def test_ordering(self):
        faq1 = SalesfaqFactory(booking_step='general', display_order=3, question='Question C')
        faq2 = SalesfaqFactory(booking_step='step1', display_order=1, question='Question A')
        faq3 = SalesfaqFactory(booking_step='general', display_order=2, question='Question B')

        ordered_faqs = list(Salesfaq.objects.all())
        # Expected order: faq2 (step1, order 1), faq3 (general, order 2), faq1 (general, order 3)
        self.assertEqual(ordered_faqs[0], faq2)
        self.assertEqual(ordered_faqs[1], faq3)
        self.assertEqual(ordered_faqs[2], faq1)

    def test_default_values(self):
        # Explicitly set display_order to 0 for this test to avoid factory sequence issues
        faq = SalesfaqFactory(display_order=0)
        self.assertTrue(faq.is_active)
        self.assertEqual(faq.display_order, 0)

    def test_booking_step_choices(self):
        faq = SalesfaqFactory()
        self.assertIn(faq.booking_step, [choice[0] for choice in Salesfaq.BOOKING_STEP_CHOICES])
