from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

# Import models and factories
from service.models import ServiceBooking
from ..test_helpers.model_factories import UserFactory, ServiceBookingFactory, ServiceTypeFactory

class AdminServiceBookingDetailViewTest(TestCase):
    """
    Tests for the AdminServiceBookingDetailView.
    Focuses on displaying specific service booking details for authorized staff.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods.
        Create a staff user and a service booking for testing.
        """
        cls.staff_user = UserFactory(username='staff_user_detail', is_staff=True, is_superuser=False)
        cls.superuser = UserFactory(username='superuser_detail', is_staff=True, is_superuser=True) # For completeness, though not explicitly tested for access denial

        # Create a service type for the booking
        cls.service_type = ServiceTypeFactory(name="Major Service")

        # Create a specific service booking to be detailed
        cls.booking = ServiceBookingFactory(
            service_type=cls.service_type,
            dropoff_date=timezone.now().date() + timezone.timedelta(days=7),
            dropoff_time=timezone.now().time(),
            booking_status='CONFIRMED',
            customer_notes="Customer requested a specific check on brakes."
        )

        # Define URL for convenience (will be formatted with booking.pk)
        cls.detail_url_name = 'service:admin_service_booking_detail'

    def setUp(self):
        """
        Set up for each test method.
        """
        self.client = Client()
        self.client.force_login(self.staff_user) # Log in staff user for all tests by default

    # --- Detail View Tests ---

    def test_get_request_displays_booking_details(self):
        """
        Test GET request to display details of a specific service booking.
        Ensures correct template, context object, and booking data.
        """
        response = self.client.get(reverse(self.detail_url_name, args=[self.booking.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'service/admin_service_booking_detail.html')

        # Check if the context contains the correct service booking object
        self.assertIn('service_booking', response.context)
        self.assertEqual(response.context['service_booking'], self.booking)

        # Check if booking_pk is correctly passed to context
        self.assertIn('booking_pk', response.context)
        self.assertEqual(response.context['booking_pk'], self.booking.pk)

        # Verify some content from the booking is present in the response
        self.assertContains(response, self.booking.service_booking_reference)
        self.assertContains(response, self.booking.service_type.name)
        self.assertContains(response, str(self.booking.dropoff_date.strftime('%Y-%m-%d')))
        self.assertContains(response, self.booking.booking_status)
        self.assertContains(response, self.booking.customer_notes)
        self.assertContains(response, self.booking.service_profile.name) # Check linked profile name
        self.assertContains(response, self.booking.customer_motorcycle.model) # Check linked motorcycle model

    def test_get_request_invalid_booking_pk(self):
        """
        Test GET request with an invalid/non-existent booking primary key.
        Should return a 404 Not Found error.
        """
        invalid_pk = self.booking.pk + 999 # A PK that should not exist
        response = self.client.get(reverse(self.detail_url_name, args=[invalid_pk]))
        self.assertEqual(response.status_code, 404)

