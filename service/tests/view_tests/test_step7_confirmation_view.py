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

    @patch('service.views.step7_confirmation_view.convert_temp_service_booking')
    def test_get_in_store_payment_flow_success(self, mock_convert):
        """
        Tests the GET request for an in-store payment, which should convert the
        TempServiceBooking to a ServiceBooking and redirect.
        """
        temp_booking = TempServiceBookingFactory()
        # Mock the return value of the converter function
        final_booking = ServiceBookingFactory()
        mock_convert.return_value = final_booking

        url = f"{self.base_url}?temp_booking_uuid={temp_booking.session_uuid}"
        response = self.client.get(url)

        # 1. Assert the converter was called once with the correct temp booking ID
        mock_convert.assert_called_once_with(temp_booking.id)

        # 2. Assert the user is redirected to the clean confirmation URL
        self.assertRedirects(response, self.base_url, status_code=302)

        # 3. Assert the final booking reference is stored in the session
        self.assertEqual(self.client.session.get('final_service_booking_reference'), final_booking.service_booking_reference)
        
        # 4. Assert the temporary booking session key is cleaned up
        self.assertNotIn('temp_service_booking_uuid', self.client.session)

    def test_get_in_store_flow_temp_booking_not_found(self):
        """
        Tests that an invalid temp_booking_uuid redirects with an error message.
        """
        invalid_uuid = uuid.uuid4()
        url = f"{self.base_url}?temp_booking_uuid={invalid_uuid}"
        response = self.client.get(url)

        self.assertRedirects(response, reverse('service:service'))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Your booking session has expired" in str(m) for m in messages))

    @patch('service.views.step7_confirmation_view.convert_temp_service_booking')
    def test_get_in_store_flow_conversion_fails(self, mock_convert):
        """
        Tests that if the conversion function fails, it redirects with an error.
        """
        temp_booking = TempServiceBookingFactory()
        mock_convert.side_effect = Exception("Conversion failed!")

        url = f"{self.base_url}?temp_booking_uuid={temp_booking.session_uuid}"
        response = self.client.get(url)

        self.assertRedirects(response, reverse('service:service'))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("An error occurred while finalizing your booking" in str(m) for m in messages))

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

    def test_get_no_identifiers_redirects_to_home(self):
        """
        Tests that accessing the page with no valid identifiers in session or URL
        redirects to the service homepage.
        """
        response = self.client.get(self.base_url)

        self.assertRedirects(response, reverse('service:service'))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Could not find a booking confirmation" in str(m) for m in messages))
