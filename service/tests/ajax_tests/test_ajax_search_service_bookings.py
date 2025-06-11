from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.http import JsonResponse
import json
from datetime import date, time, timedelta

# Import all necessary factories from your model_factories.py
from ..test_helpers.model_factories import (
    UserFactory,
    ServiceProfileFactory,
    CustomerMotorcycleFactory,
    ServiceTypeFactory,
    ServiceBookingFactory,
    PaymentFactory, # Assuming PaymentFactory is available for ServiceBooking
)

# Import the view function to be tested
from service.ajax.ajax_search_service_bookings import search_service_bookings_ajax

class AjaxSearchServiceBookingsTest(TestCase):
    """
    Tests for the AJAX view `search_service_bookings_ajax`.
    This test suite utilizes model factories to create actual database objects
    for more realistic testing of the search functionality across multiple fields.
    """

    def setUp(self):
        """
        Set up for each test method.
        Initialize a RequestFactory to create dummy request objects.
        Create a staff user for authentication.
        Create various ServiceBooking instances with linked data for comprehensive testing.
        """
        self.factory = RequestFactory()

        # Create a staff user for authentication, as the view requires login and is_staff
        self.staff_user = UserFactory(username='admin_user', email='admin@example.com', is_staff=True)
        self.non_staff_user = UserFactory(username='regular_user', email='user@example.com', is_staff=False)


        # --- Create Service Booking Scenarios ---

        # Booking 1: Specific reference, customer John Doe, Honda motorcycle, Oil Change service
        self.profile1 = ServiceProfileFactory(name='John Doe', email='john.doe@example.com', phone_number='0411111111')
        self.motorcycle1 = CustomerMotorcycleFactory(service_profile=self.profile1, brand='Honda', model='CBR600RR', year='2020', rego='JD001')
        self.service_type1 = ServiceTypeFactory(name='Oil Change', description='Standard oil and filter replacement')
        self.payment1 = PaymentFactory(status='paid')
        self.booking1 = ServiceBookingFactory(
            service_booking_reference='SVC-ABCDEF01',
            service_profile=self.profile1,
            customer_motorcycle=self.motorcycle1,
            service_type=self.service_type1,
            dropoff_date=date.today() + timedelta(days=5),
            dropoff_time=time(10, 0),
            booking_status='confirmed',
            payment_status='paid',
            payment=self.payment1,
            customer_notes='Customer prefers synthetic oil.'
        )

        # Booking 2: Another customer Jane Smith, Yamaha motorcycle, Tyre Replacement service
        self.profile2 = ServiceProfileFactory(name='Jane Smith', email='jane.smith@example.com', phone_number='0422222222')
        self.motorcycle2 = CustomerMotorcycleFactory(service_profile=self.profile2, brand='Yamaha', model='YZF-R1', year='2022', rego='JS002')
        self.service_type2 = ServiceTypeFactory(name='Tyre Replacement', description='Front and rear tyre replacement')
        self.payment2 = PaymentFactory(status='deposit_paid')
        self.booking2 = ServiceBookingFactory(
            service_booking_reference='SVC-XYZ78902',
            service_profile=self.profile2,
            customer_motorcycle=self.motorcycle2,
            service_type=self.service_type2,
            dropoff_date=date.today() + timedelta(days=10),
            dropoff_time=time(14, 30),
            booking_status='pending',
            payment_status='deposit_paid',
            payment=self.payment2,
            customer_notes='Need urgent service for racing.'
        )

        # Booking 3: Customer Bob Johnson, Kawasaki motorcycle, Major Service, Cancelled
        self.profile3 = ServiceProfileFactory(name='Bob Johnson', email='bob.j@example.com', phone_number='0433333333')
        self.motorcycle3 = CustomerMotorcycleFactory(service_profile=self.profile3, brand='Kawasaki', model='Ninja 400', year='2019', rego='BJ003')
        self.service_type3 = ServiceTypeFactory(name='Major Service', description='Full inspection and service')
        self.payment3 = PaymentFactory(status='refunded')
        self.booking3 = ServiceBookingFactory(
            service_booking_reference='SVC-PQRSTU03',
            service_profile=self.profile3,
            customer_motorcycle=self.motorcycle3,
            service_type=self.service_type3,
            dropoff_date=date.today() + timedelta(days=2),
            dropoff_time=time(9, 0),
            booking_status='cancelled',
            payment_status='refunded',
            payment=self.payment3,
            customer_notes='Decided to sell the bike.'
        )

        # Booking 4: Customer Alice, Suzuki motorcycle, General Check, No notes, Unpaid
        self.profile4 = ServiceProfileFactory(name='Alice Wonderland', email='alice.w@example.com', phone_number='0444444444')
        self.motorcycle4 = CustomerMotorcycleFactory(service_profile=self.profile4, brand='Suzuki', model='GSX-R1000', year='2021', rego='AW004')
        self.service_type4 = ServiceTypeFactory(name='General Check', description='Pre-purchase inspection')
        self.payment4 = PaymentFactory(status='unpaid', amount=0) # Set amount to 0 for unpaid
        self.booking4 = ServiceBookingFactory(
            service_booking_reference='SVC-GHIJKL04',
            service_profile=self.profile4,
            customer_motorcycle=self.motorcycle4,
            service_type=self.service_type4,
            dropoff_date=date.today() + timedelta(days=1),
            dropoff_time=time(11, 0),
            booking_status='pending',
            payment_status='unpaid',
            payment=self.payment4,
            customer_notes='' # Empty notes
        )

    def _make_request(self, query_term, user=None):
        """Helper to create and send a GET request to the AJAX view."""
        url = reverse('service:admin_api_search_bookings')
        if query_term:
            url += f'?query={query_term}'
        request = self.factory.get(url)
        if user:
            request.user = user
        else: # Default to staff user if no user is provided
            request.user = self.staff_user
        return search_service_bookings_ajax(request)

    def test_search_by_booking_reference(self):
        """Test searching by full or partial booking reference."""
        response = self._make_request(query_term='ABCDEF01')
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(len(content['bookings']), 1)
        self.assertEqual(content['bookings'][0]['reference'], self.booking1.service_booking_reference)

        response = self._make_request(query_term='SVC-XYZ') # Partial match
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(len(content['bookings']), 1)
        self.assertEqual(content['bookings'][0]['reference'], self.booking2.service_booking_reference)

    def test_search_by_customer_name(self):
        """Test searching by customer's full name."""
        response = self._make_request(query_term='John Doe')
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(len(content['bookings']), 1)
        self.assertEqual(content['bookings'][0]['customer_name'], self.profile1.name)

        response = self._make_request(query_term='Smith') # Partial name
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(len(content['bookings']), 1)
        self.assertEqual(content['bookings'][0]['customer_name'], self.profile2.name)

    def test_search_by_customer_email(self):
        """Test searching by customer's email address."""
        response = self._make_request(query_term='jane.smith@example.com')
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(len(content['bookings']), 1)
        self.assertEqual(content['bookings'][0]['customer_name'], self.profile2.name)

    def test_search_by_motorcycle_brand_model_year(self):
        """Test searching by motorcycle brand, model, or year."""
        response = self._make_request(query_term='Honda') # Brand
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(len(content['bookings']), 1)
        self.assertIn('Honda', content['bookings'][0]['motorcycle_info'])

        response = self._make_request(query_term='CBR600RR') # Model
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(len(content['bookings']), 1)
        self.assertIn('CBR600RR', content['bookings'][0]['motorcycle_info'])

        response = self._make_request(query_term='2022') # Year
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(len(content['bookings']), 1)
        self.assertIn('2022', content['bookings'][0]['motorcycle_info'])

        response = self._make_request(query_term='GSX-R1000') # Another model
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(len(content['bookings']), 1)
        self.assertIn('Suzuki', content['bookings'][0]['motorcycle_info'])

    def test_search_by_rego(self):
        """Test searching by motorcycle license plate."""
        response = self._make_request(query_term='AW004')
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(len(content['bookings']), 1)
        self.assertEqual(content['bookings'][0]['customer_name'], self.profile4.name)

    def test_search_by_service_type_name_description(self):
        """Test searching by service type name or description."""
        response = self._make_request(query_term='Oil Change') # Name
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(len(content['bookings']), 1)
        self.assertEqual(content['bookings'][0]['service_type_name'], self.service_type1.name)

        response = self._make_request(query_term='inspection') # Description (partial)
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(content['bookings'][0]['service_type_name'], self.service_type4.name)

    def test_search_by_booking_status(self):
        """Test searching by booking status."""
        response = self._make_request(query_term='confirmed')
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(len(content['bookings']), 1)
        self.assertEqual(content['bookings'][0]['booking_status'], 'Confirmed')

        response = self._make_request(query_term='pending')
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(len(content['bookings']), 2) # booking2 and booking4 are 'pending'

    def test_search_by_customer_notes(self):
        """Test searching by customer notes."""
        response = self._make_request(query_term='synthetic oil')
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(len(content['bookings']), 1)
        self.assertEqual(content['bookings'][0]['reference'], self.booking1.service_booking_reference)

    def test_search_multiple_matches_and_ordering(self):
        """
        Test searching where multiple bookings match, ensuring correct ordering (by dropoff_date descending).
        Bookings with 'pending' status: booking2 (dropoff_date +10 days), booking4 (dropoff_date +1 day)
        Expected order: booking2, then booking4
        """
        response = self._make_request(query_term='pending')
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(len(content['bookings']), 2)
        # Check order by dropoff_date (most recent first)
        self.assertEqual(content['bookings'][0]['reference'], self.booking2.service_booking_reference)
        self.assertEqual(content['bookings'][1]['reference'], self.booking4.service_booking_reference)

    def test_search_no_matches(self):
        """Test searching for a term that should yield no matches."""
        response = self._make_request(query_term='NonExistentBookingTerm')
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(len(content['bookings']), 0)
        self.assertEqual(content['bookings'], [])

    def test_search_empty_query(self):
        """Test that an empty search query returns an empty list of bookings."""
        response = self._make_request(query_term='')
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(len(content['bookings']), 0)
        self.assertEqual(content['bookings'], [])

    def test_search_no_query_parameter(self):
        """Test that no 'query' parameter also returns an empty list of bookings."""
        url = reverse('service:admin_api_search_bookings')
        request = self.factory.get(url)
        request.user = self.staff_user # Authenticate as staff
        response = search_service_bookings_ajax(request)

        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertIn('bookings', content)
        self.assertEqual(len(content['bookings']), 0)
        self.assertEqual(content['bookings'], [])

    def test_only_get_requests_allowed(self):
        """
        Test that only GET requests are allowed for this view.
        (The @require_GET decorator handles this).
        """
        url = reverse('service:admin_api_search_bookings')
        request = self.factory.post(url) # Send a POST request
        request.user = self.staff_user # Authenticate as staff

        response = search_service_bookings_ajax(request)

        # @require_GET decorator returns 405 Method Not Allowed for non-GET requests
        self.assertEqual(response.status_code, 405)

    def test_permission_denied_for_non_staff_user(self):
        """Test that a non-staff user gets a 403 Permission Denied response."""
        response = self._make_request(query_term='John Doe', user=self.non_staff_user)
        self.assertEqual(response.status_code, 403)
        content = json.loads(response.content)
        self.assertIn('error', content)
        self.assertEqual(content['error'], 'Permission denied')
