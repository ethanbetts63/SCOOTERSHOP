# service/tests/test_step7_confirmation_view.py
from django.test import TestCase
from django.urls import reverse
from django.contrib.messages import get_messages
from unittest.mock import patch, Mock
import uuid

from service.models import ServiceBooking, TempServiceBooking
from payments.models import Payment
from ..test_helpers.model_factories import (
    UserFactory,
    ServiceBookingFactory,
    TempServiceBookingFactory,
    PaymentFactory,
)

# Views to be tested
from service.views.v2_views.user_views.step7_confirmation_view import Step7ConfirmationView

class ServiceBookingConfirmationViewTest(TestCase):
    """
    Tests for the ServiceBookingConfirmationView (Step 7).
    Updated to reflect that temp booking conversion happens BEFORE this view.
    """

    @classmethod
    def setUpTestData(cls):
        """Set up non-modified objects used by all test methods."""
        cls.user = UserFactory()
        cls.base_url = reverse('service:service_book_step7')

    def setUp(self):
        """Set up for each test method."""
        self.client.force_login(self.user)
        # Clean up models to ensure isolation between tests
        TempServiceBooking.objects.all().delete()
        ServiceBooking.objects.all().delete()
        Payment.objects.all().delete()

    # Removed tests related to temp_booking_uuid and convert_temp_service_booking
    # as these scenarios should now be handled before reaching Step7ConfirmationView.
    # test_get_in_store_payment_flow_success is removed.
    # test_get_in_store_flow_temp_booking_not_found is removed.
    # test_get_in_store_flow_conversion_fails is removed.


    def test_get_booking_found_by_session_reference(self):
        """
        Tests retrieving a confirmed booking using the reference from the session.
        """
        final_booking = ServiceBookingFactory()
        session = self.client.session
        session['final_service_booking_reference'] = final_booking.service_booking_reference
        session.save()

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'service/step7_confirmation.html')
        self.assertEqual(response.context['service_booking'].id, final_booking.id)
        self.assertFalse(response.context['is_processing'])
        # Ensure temp_service_booking_uuid is cleared if it was somehow present
        self.assertNotIn('temp_service_booking_uuid', self.client.session)


    def test_get_booking_found_by_payment_intent_id(self):
        """
        Tests retrieving a confirmed booking using a payment_intent_id from the URL.
        """
        payment_intent_id = f"pi_{uuid.uuid4().hex}"
        final_booking = ServiceBookingFactory(stripe_payment_intent_id=payment_intent_id)
        
        url = f"{self.base_url}?payment_intent_id={payment_intent_id}"
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'service/step7_confirmation.html')
        self.assertEqual(response.context['service_booking'].id, final_booking.id)
        self.assertFalse(response.context['is_processing'])
        self.assertEqual(self.client.session.get('final_service_booking_reference'), final_booking.service_booking_reference)
        # Ensure temp_service_booking_uuid is cleared if it was somehow present
        self.assertNotIn('temp_service_booking_uuid', self.client.session)


    def test_get_booking_processing_due_to_webhook_delay(self):
        """
        Tests the "processing" state when a ServiceBooking is not yet created
        but a Payment object exists for the given payment_intent_id.
        """
        payment_intent_id = f"pi_{uuid.uuid4().hex}"
        # Create a Payment record, but no associated ServiceBooking yet
        PaymentFactory(stripe_payment_intent_id=payment_intent_id)

        url = f"{self.base_url}?payment_intent_id={payment_intent_id}"
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'service/step7_confirmation.html')
        self.assertTrue(response.context['is_processing'])
        self.assertEqual(response.context['payment_intent_id'], payment_intent_id)
        self.assertNotIn('service_booking', response.context)
        # Ensure temp_service_booking_uuid is cleared if it was somehow present
        self.assertNotIn('temp_service_booking_uuid', self.client.session)


    def test_get_no_identifiers_redirects_to_home(self):
        """
        Tests that accessing the page with no valid identifiers in session or URL
        redirects to the service homepage with a warning message.
        """
        response = self.client.get(self.base_url)

        self.assertRedirects(response, reverse('service:service'))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Could not find a booking confirmation. Please start over if you have not booked." in str(m) for m in messages))


    def test_get_session_reference_invalid_then_redirects_to_home(self):
        """
        Tests that if a session reference exists but points to a non-existent booking,
        it clears the session and redirects to home.
        """
        invalid_booking_reference = "NONEXISTENTREF123"
        session = self.client.session
        session['final_service_booking_reference'] = invalid_booking_reference
        session.save()

        response = self.client.get(self.base_url)
        
        self.assertRedirects(response, reverse('service:service'))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Could not find a booking confirmation" in str(m) for m in messages))
        self.assertNotIn('final_service_booking_reference', self.client.session) # Should be cleared

    def test_get_payment_intent_id_invalid_no_payment_or_booking_redirects_to_home(self):
        """
        Tests that if a payment_intent_id is provided but no corresponding Payment
        or ServiceBooking exists, it redirects to the home page with an error.
        This covers cases where the webhook might have totally failed.
        """
        payment_intent_id = f"pi_{uuid.uuid4().hex}"
        # Ensure no payment or service booking exists for this ID

        url = f"{self.base_url}?payment_intent_id={payment_intent_id}"
        response = self.client.get(url)

        self.assertRedirects(response, reverse('service:service'))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Could not find a booking confirmation" in str(m) for m in messages))

