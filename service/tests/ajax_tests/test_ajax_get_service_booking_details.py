from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.http import JsonResponse
import json
from decimal import Decimal
import datetime
from django.utils import timezone

# Import the view function to be tested
from service.ajax.ajax_get_service_booking_details import get_service_booking_details_json

# Import your factories
from ..test_helpers.model_factories import (
    ServiceBookingFactory, 
    ServiceProfileFactory, 
    CustomerMotorcycleFactory, 
    ServiceTypeFactory,
    PaymentFactory,
    RefundPolicySettingsFactory, 
    UserFactory
)
# Assuming service.models.ServiceBooking is where ServiceBooking is defined
from service.models import ServiceBooking 


class AjaxGetServiceBookingDetailsTest(TestCase):
    """
    Tests for the AJAX view `get_service_booking_details_json`.
    This test suite utilizes model factories to create actual database objects
    for more realistic testing.
    """

    def setUp(self):
        """
        Set up for each test method.
        Initialize a RequestFactory to create dummy request objects.
        Create a staff user, a regular user, and a ServiceBooking instance with related objects.
        """
        self.factory = RequestFactory()
        
        # Create a staff user for authorized requests
        self.staff_user = UserFactory(is_staff=True, username='staffuser', email='staff@example.com')
        # Create a regular user for unauthorized requests
        self.regular_user = UserFactory(is_staff=False, username='regularuser', email='regular@example.com')

        # Create a ServiceBooking instance with all necessary related objects
        # Factory will automatically create linked ServiceProfile, ServiceType, CustomerMotorcycle, Payment
        self.service_booking = ServiceBookingFactory(
            service_profile=ServiceProfileFactory(user=self.staff_user), # Link to staff user's profile
            service_type=ServiceTypeFactory(),
            customer_motorcycle=CustomerMotorcycleFactory(),
            payment=PaymentFactory(
                amount=Decimal('150.00'),
                status='paid',
                refund_policy_snapshot={"some_policy_detail": "value"} # Ensure snapshot is a dict
            ),
            # Set specific dates/times for predictable refund calculation
            dropoff_date=timezone.localdate() + datetime.timedelta(days=7),
            dropoff_time=datetime.time(10, 0),
            service_date=timezone.localdate() + datetime.timedelta(days=7),
            estimated_pickup_date=timezone.localdate() + datetime.timedelta(days=9),
            booking_status='confirmed',
            customer_notes='Test notes for booking details.'
        )

        # Ensure the payment links back to the service booking for full integrity, if needed
        # self.service_booking.payment.service_booking = self.service_booking
        # self.service_booking.payment.save()

    def test_get_service_booking_details_success(self):
        """
        Test that the view correctly returns detailed information for a valid ServiceBooking ID
        when accessed by a staff user.
        """
        url = reverse('service:admin_api_get_service_booking_details', args=[self.service_booking.pk])
        request = self.factory.get(url)
        request.user = self.staff_user  # Authenticate as staff user

        response = get_service_booking_details_json(request, pk=self.service_booking.pk)

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response, JsonResponse)
        content = json.loads(response.content)

        # Assertions for core booking details
        self.assertEqual(content['id'], self.service_booking.id)
        self.assertEqual(content['service_booking_reference'], self.service_booking.service_booking_reference)
        self.assertEqual(content['customer_name'], self.service_booking.service_profile.user.get_full_name() or self.service_booking.service_profile.name)
        self.assertEqual(content['service_date'], self.service_booking.service_date.strftime('%Y-%m-%d'))
        self.assertEqual(content['dropoff_date'], self.service_booking.dropoff_date.strftime('%Y-%m-%d'))
        self.assertEqual(content['dropoff_time'], self.service_booking.dropoff_time.strftime('%H:%M'))
        self.assertEqual(content['estimated_pickup_date'], self.service_booking.estimated_pickup_date.strftime('%Y-%m-%d'))
        self.assertEqual(content['booking_status'], self.service_booking.get_booking_status_display())
        self.assertEqual(content['customer_notes'], self.service_booking.customer_notes)

        # Assertions for nested motorcycle details
        self.assertIn('motorcycle_details', content)
        self.assertEqual(content['motorcycle_details']['year'], int(self.service_booking.customer_motorcycle.year))
        self.assertEqual(content['motorcycle_details']['brand'], self.service_booking.customer_motorcycle.brand)
        self.assertEqual(content['motorcycle_details']['model'], self.service_booking.customer_motorcycle.model)

        # Assertions for nested service type details
        self.assertIn('service_type_details', content)
        self.assertEqual(content['service_type_details']['name'], self.service_booking.service_type.name)
        self.assertEqual(content['service_type_details']['description'], self.service_booking.service_type.description)
        self.assertAlmostEqual(Decimal(str(content['service_type_details']['base_price'])), self.service_booking.service_type.base_price)

        # Assertions for payment information
        self.assertEqual(content['payment_option'], self.service_booking.get_payment_option_display())
        self.assertEqual(content['payment_date'], self.service_booking.payment.created_at.strftime('%Y-%m-%d %H:%M'))
        self.assertAlmostEqual(Decimal(str(content['payment_amount'])), self.service_booking.payment.amount)
        self.assertEqual(content['payment_status'], self.service_booking.get_payment_status_display())

        # Assertions for refund information
        self.assertIn('entitled_refund_amount', content)
        self.assertIn('refund_calculation_details', content)
        self.assertIn('refund_policy_applied', content)
        self.assertIn('refund_days_before_dropoff', content)
        self.assertIn('refund_request_status_for_booking', content)
        
        # CORRECTED: Assert that 'refund_calculation_details' is a string, not a dict from JSON.loads
        self.assertIsInstance(content['refund_calculation_details'], str)
        # You could also add a basic check for the content if you wish:
        self.assertIn('Cancellation', content['refund_calculation_details'])


    def test_get_service_booking_details_not_found(self):
        """
        Test that the view returns a 404 error if the ServiceBooking ID does not exist.
        """
        invalid_pk = self.service_booking.pk + 100 # An ID that surely doesn't exist

        url = reverse('service:admin_api_get_service_booking_details', args=[invalid_pk])
        request = self.factory.get(url)
        request.user = self.staff_user # Authenticate as staff user

        response = get_service_booking_details_json(request, pk=invalid_pk)

        self.assertEqual(response.status_code, 404)
        self.assertIsInstance(response, JsonResponse)
        content = json.loads(response.content)
        self.assertIn('error', content)
        self.assertEqual(content['error'], 'Service Booking not found')

    def test_get_service_booking_details_permission_denied(self):
        """
        Test that the view returns a 403 error if a non-staff user attempts to access it.
        """
        url = reverse('service:admin_api_get_service_booking_details', args=[self.service_booking.pk])
        request = self.factory.get(url)
        request.user = self.regular_user # Authenticate as a regular user

        response = get_service_booking_details_json(request, pk=self.service_booking.pk)

        self.assertEqual(response.status_code, 403)
        self.assertIsInstance(response, JsonResponse)
        content = json.loads(response.content)
        self.assertIn('error', content)
        self.assertEqual(content['error'], 'Permission denied')

    def test_only_get_requests_allowed(self):
        """
        Test that only GET requests are allowed for this view (@require_GET decorator).
        """
        url = reverse('service:admin_api_get_service_booking_details', args=[self.service_booking.pk])
        
        # Try a POST request
        request = self.factory.post(url)
        request.user = self.staff_user # Still needs a user for @login_required

        response = get_service_booking_details_json(request, pk=self.service_booking.pk)

        self.assertEqual(response.status_code, 405) # Method Not Allowed

