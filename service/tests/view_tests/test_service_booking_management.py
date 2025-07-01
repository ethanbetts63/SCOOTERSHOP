from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

                             
from service.models import ServiceBooking, ServiceType, BlockedServiceDate
from ..test_helpers.model_factories import UserFactory, ServiceBookingFactory, ServiceTypeFactory

class ServiceBookingManagementViewTest(TestCase):
    """
    Tests for the ServiceBookingManagementView.
    Covers access control and listing of service bookings.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods.
        Create various users and service bookings for testing different scenarios.
        """
        cls.staff_user = UserFactory(username='staff_user_booking', is_staff=True, is_superuser=False)
        cls.superuser = UserFactory(username='superuser_booking', is_staff=True, is_superuser=True)
        cls.regular_user = UserFactory(username='regular_user_booking', is_staff=False, is_superuser=False)

                                   
        cls.service_type_a = ServiceTypeFactory(name="Oil Change")
        cls.service_type_b = ServiceTypeFactory(name="Tyre Replacement")

                                                                          
        cls.booking1 = ServiceBookingFactory(
            service_type=cls.service_type_a,
            dropoff_date=timezone.now().date() - timezone.timedelta(days=5),
            dropoff_time=timezone.now().time(),
            booking_status='CONFIRMED'
        )
        cls.booking2 = ServiceBookingFactory(
            service_type=cls.service_type_b,
            dropoff_date=timezone.now().date() - timezone.timedelta(days=1),
            dropoff_time=timezone.now().time(),
            booking_status='PENDING'
        )
        cls.booking3 = ServiceBookingFactory(
            service_type=cls.service_type_a,
            dropoff_date=timezone.now().date() + timezone.timedelta(days=10),
            dropoff_time=timezone.now().time(),
            booking_status='COMPLETED'
        )

                                    
        cls.list_url = reverse('service:service_booking_management')

    def setUp(self):
        """
        Set up for each test method.
        """
        self.client = Client()

    def test_view_grants_access_to_staff_user(self):
        """
        Ensure staff users can access the view.
        """
        self.client.force_login(self.staff_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)

    def test_view_grants_access_to_superuser(self):
        """
        Ensure superusers can access the view.
        """
        self.client.force_login(self.superuser)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)

                                         

    def test_get_request_list_all_bookings(self):
        """
        Test GET request to list all service bookings.
        Ensures correct template, context variables, and ordering.
        """
        self.client.force_login(self.staff_user)
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'service/service_booking_management.html')
        self.assertIn('bookings', response.context)
        self.assertIn('page_title', response.context)
        self.assertIn('active_tab', response.context)
        self.assertEqual(response.context['page_title'], 'Manage Service Bookings')
        self.assertEqual(response.context['active_tab'], 'service_bookings')

                                                                                              
        bookings_in_context = list(response.context['bookings'])
                                                                                 
                                                                                 
        expected_bookings = [self.booking3, self.booking2, self.booking1]
        self.assertListEqual(bookings_in_context, expected_bookings)
        self.assertEqual(len(bookings_in_context), ServiceBooking.objects.count())

    def test_get_request_no_bookings(self):
        """
        Test GET request when there are no service bookings.
        """
        ServiceBooking.objects.all().delete()                                             
        self.client.force_login(self.staff_user)
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'service/service_booking_management.html')
        self.assertIn('bookings', response.context)
        self.assertEqual(len(response.context['bookings']), 0)
        self.assertEqual(response.context['page_title'], 'Manage Service Bookings')

