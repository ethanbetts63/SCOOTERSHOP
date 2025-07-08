
from django.test import TestCase
from service.models import Servicefaq
from service.tests.test_helpers.model_factories import ServicefaqFactory

class ServicefaqModelTest(TestCase):

    def test_servicefaq_creation(self):
        faq = Servicefaq.objects.create(
            booking_step='general',
            question='Test Question',
            answer='Test Answer',
            is_active=True,
            display_order=1
        )
        self.assertIsInstance(faq, Servicefaq)
        self.assertEqual(faq.booking_step, 'general')
        self.assertEqual(faq.question, 'Test Question')
        self.assertEqual(faq.answer, 'Test Answer')
        self.assertTrue(faq.is_active)
        self.assertEqual(faq.display_order, 1)
        self.assertIsNotNone(faq.created_at)
        self.assertIsNotNone(faq.updated_at)

    def test_str_representation(self):
        faq = ServicefaqFactory(question='Another Question', booking_step='step1')
        self.assertEqual(str(faq), 'Q: Another Question (Step 1: Service Details)')

    def test_ordering(self):
        # Create FAQs with distinct booking_step and display_order to ensure predictable ordering
        faq1 = ServicefaqFactory(booking_step='general', display_order=3, question='Question C')
        faq2 = ServicefaqFactory(booking_step='step1', display_order=1, question='Question A')
        faq3 = ServicefaqFactory(booking_step='general', display_order=2, question='Question B')

        ordered_faqs = list(Servicefaq.objects.all())
        # Expected order based on model's Meta.ordering = ["booking_step", "display_order", "question"]
        # 'general' comes after 'service_page', 'step1', etc. alphabetically.
        # So, 'step1' FAQs come before 'general' FAQs.
        # Within 'general', they are ordered by display_order, then question.
        self.assertEqual(ordered_faqs[0], faq2) # step1, order 1
        self.assertEqual(ordered_faqs[1], faq3) # general, order 2
        self.assertEqual(ordered_faqs[2], faq1) # general, order 3

    def test_default_values(self):
        faq = ServicefaqFactory(display_order=0)
        self.assertTrue(faq.is_active)
        self.assertEqual(faq.display_order, 0)

    def test_booking_step_choices(self):
        faq = ServicefaqFactory()
        self.assertIn(faq.booking_step, [choice[0] for choice in Servicefaq.BOOKING_STEP_CHOICES])
