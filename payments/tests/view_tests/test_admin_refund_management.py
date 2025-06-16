# payments/tests/views/test_admin_refund_management.py

from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch, MagicMock
from decimal import Decimal

from payments.models import RefundRequest
# CORRECTED IMPORT PATH:
from payments.views.Refunds.admin_refund_management import AdminRefundManagement 
from payments.tests.test_helpers.model_factories import (
    RefundRequestFactory, HireBookingFactory, ServiceBookingFactory, SalesBookingFactory,
    UserFactory, DriverProfileFactory, ServiceProfileFactory, SalesProfileFactory,
    PaymentFactory
)

User = get_user_model()

class AdminRefundManagementTests(TestCase):
    """
    Tests for the AdminRefundManagement ListView.
    This class covers the display, filtering, and cleaning logic of the admin
    refund management interface.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up test data for the entire test class.
        Includes creating a staff user and various types of refund requests.
        """
        cls.staff_user = UserFactory(is_staff=True)
        cls.non_staff_user = UserFactory(is_staff=False)

        # Create different types of booking objects and associated profiles
        cls.hire_booking_1 = HireBookingFactory(amount_paid=Decimal('100.00'))
        cls.driver_profile_1 = DriverProfileFactory(user=UserFactory(email='driver1@example.com'))
        cls.hire_booking_1.driver_profile = cls.driver_profile_1 # Ensure link is strong

        cls.service_booking_1 = ServiceBookingFactory(amount_paid=Decimal('200.00'))
        cls.service_profile_1 = ServiceProfileFactory(user=UserFactory(email='service1@example.com'))
        cls.service_booking_1.service_profile = cls.service_profile_1 # Ensure link is strong

        cls.sales_booking_1 = SalesBookingFactory(amount_paid=Decimal('300.00'))
        cls.sales_profile_1 = SalesProfileFactory(user=UserFactory(email='sales1@example.com'))
        cls.sales_booking_1.sales_profile = cls.sales_profile_1 # Ensure link is strong

        # Create RefundRequest instances with different statuses and associated bookings
        cls.req_pending_hire = RefundRequestFactory(
            status='pending',
            hire_booking=cls.hire_booking_1,
            driver_profile=cls.driver_profile_1,
            request_email='test_pending_hire@example.com',
            amount_to_refund=Decimal('100.00'),
            refund_calculation_details={'details': 'Hire Full Refund'}
        )
        cls.req_approved_service = RefundRequestFactory(
            status='approved',
            service_booking=cls.service_booking_1,
            service_profile=cls.service_profile_1,
            request_email='test_approved_service@example.com',
            amount_to_refund=Decimal('200.00'),
            refund_calculation_details={'details': 'Service Full Refund'}
        )
        cls.req_rejected_sales = RefundRequestFactory(
            status='rejected',
            sales_booking=cls.sales_booking_1,
            sales_profile=cls.sales_profile_1,
            request_email='test_rejected_sales@example.com',
            amount_to_refund=Decimal('0.00'),
            rejection_reason='Customer changed mind',
            refund_calculation_details={'details': 'Sales No Refund'}
        )
        cls.req_unverified_old = RefundRequestFactory(
            status='unverified',
            request_email='old_unverified@example.com',
            token_created_at=timezone.now() - timedelta(hours=25), # Older than 24 hours
            hire_booking=HireBookingFactory(), # Link to a dummy booking for realism
            driver_profile=DriverProfileFactory(user=UserFactory(email='old_unverified_driver@example.com'))
        )
        cls.req_unverified_new = RefundRequestFactory(
            status='unverified',
            request_email='new_unverified@example.com',
            token_created_at=timezone.now() - timedelta(hours=1), # Within 24 hours
            service_booking=ServiceBookingFactory(), # Link to a dummy booking
            service_profile=ServiceProfileFactory(user=UserFactory(email='new_unverified_service@example.com'))
        )
        cls.req_refunded_sales = RefundRequestFactory(
            status='refunded',
            sales_booking=SalesBookingFactory(),
            sales_profile=SalesProfileFactory(user=UserFactory(email='refunded_sales@example.com')),
            request_email='test_refunded_sales@example.com',
            amount_to_refund=Decimal('150.00'),
            stripe_refund_id='re_sales_123',
            refund_calculation_details={'details': 'Sales Partial Refund'}
        )
        cls.req_partially_refunded_hire = RefundRequestFactory(
            status='partially_refunded',
            hire_booking=HireBookingFactory(),
            driver_profile=DriverProfileFactory(user=UserFactory(email='partially_refunded_hire@example.com')),
            request_email='test_partially_refunded_hire@example.com',
            amount_to_refund=Decimal('50.00'),
            stripe_refund_id='re_hire_partial_456',
            refund_calculation_details={'details': 'Hire Partial Refund'}
        )

    def setUp(self):
        """
        Set up for each test method.
        Initializes RequestFactory and sets up a logged-in staff user.
        """
        self.factory = RequestFactory()
        self.client.force_login(self.staff_user) # Ensure staff user is logged in for view access

    def test_staff_member_required_decorator(self):
        """
        Ensures only staff users can access the view.
        """
        self.client.logout() # Log out staff user
        self.client.force_login(self.non_staff_user)
        # CORRECTED URL REVERSE:
        response = self.client.get(reverse('payments:admin_refund_management'))
        # Should redirect to admin login if not staff
        self.assertEqual(response.status_code, 302) 
        self.assertTrue(reverse('admin:login') in response.url)

        self.client.logout() # Ensure no user is logged in
        # CORRECTED URL REVERSE:
        response = self.client.get(reverse('payments:admin_refund_management'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(reverse('admin:login') in response.url)

        self.client.force_login(self.staff_user)
        # CORRECTED URL REVERSE:
        response = self.client.get(reverse('payments:admin_refund_management'))
        self.assertEqual(response.status_code, 200) # Staff user should get OK

    @patch('payments.views.Refunds.admin_refund_management.send_templated_email') # Corrected patch path
    def test_clean_expired_unverified_refund_requests(self, mock_send_email):
        """
        Tests that old unverified requests are deleted and emails are sent.
        """
        initial_count = RefundRequest.objects.filter(status='unverified').count()
        self.assertEqual(initial_count, 2) # Both old and new unverified requests exist initially

        # Call the view's method directly or via a request to trigger it
        # CORRECTED URL REVERSE for RequestFactory.get:
        request = self.factory.get(reverse('payments:admin_refund_management'))
        request.user = self.staff_user # Assign a user to the request
        view = AdminRefundManagement()
        view.request = request
        view.clean_expired_unverified_refund_requests()

        # Only the new unverified request should remain
        remaining_unverified_count = RefundRequest.objects.filter(status='unverified').count()
        self.assertEqual(remaining_unverified_count, 1)
        self.assertFalse(RefundRequest.objects.filter(pk=self.req_unverified_old.pk).exists())
        self.assertTrue(RefundRequest.objects.filter(pk=self.req_unverified_new.pk).exists())

        # Assert that an email was sent for the deleted request
        mock_send_email.assert_called_once()
        # Verify call arguments - NOW ACCESSING recipient_list from call_kwargs
        call_args, call_kwargs = mock_send_email.call_args
        self.assertIn('old_unverified@example.com', call_kwargs['recipient_list']) # Corrected access
        self.assertIn(f"Booking {self.req_unverified_old.hire_booking.booking_reference}", call_kwargs['subject'])
        self.assertEqual(call_kwargs['booking'], self.req_unverified_old.hire_booking)
        self.assertEqual(call_kwargs['driver_profile'], self.req_unverified_old.driver_profile)
        self.assertIsNone(call_kwargs['service_profile'])
        self.assertIsNone(call_kwargs['sales_profile'])

    def test_get_queryset_no_filter(self):
        """
        Tests that all active requests are returned when no status filter is applied,
        and cleaning happens.
        """
        # Ensure cleanup runs before counting
        # Call clean_expired_unverified_refund_requests directly here to ensure consistent state
        # without relying on a previous test's side effects or mocking issues.
        request_for_cleanup = self.factory.get(reverse('payments:admin_refund_management'))
        request_for_cleanup.user = self.staff_user
        view_for_cleanup = AdminRefundManagement()
        view_for_cleanup.request = request_for_cleanup
        with patch('payments.views.Refunds.admin_refund_management.send_templated_email'): # Mock email sending for cleanup
            view_for_cleanup.clean_expired_unverified_refund_requests()

        request = self.factory.get(reverse('payments:admin_refund_management'))
        request.user = self.staff_user
        view = AdminRefundManagement()
        view.request = request
        with patch('payments.views.Refunds.admin_refund_management.send_templated_email'): # Mock for get_queryset call
            queryset = view.get_queryset()

        # Expected requests after old unverified is deleted:
        # req_pending_hire, req_approved_service, req_rejected_sales,
        # req_unverified_new, req_refunded_sales, req_partially_refunded_hire
        expected_pks = {
            self.req_pending_hire.pk,
            self.req_approved_service.pk,
            self.req_rejected_sales.pk,
            self.req_unverified_new.pk,
            self.req_refunded_sales.pk,
            self.req_partially_refunded_hire.pk
        }
        actual_pks = {obj.pk for obj in queryset}
        self.assertEqual(len(queryset), len(expected_pks))
        self.assertEqual(actual_pks, expected_pks)
        # mock_send_email.assert_not_called() # This assertion needs to be careful with global mocks. Better to patch locally.

    def test_get_queryset_status_filter(self):
        """
        Tests that queryset is filtered correctly by status.
        """
        # Run cleanup first to ensure consistent state
        request_for_cleanup = self.factory.get(reverse('payments:admin_refund_management'))
        request_for_cleanup.user = self.staff_user
        view_for_cleanup = AdminRefundManagement()
        view_for_cleanup.request = request_for_cleanup
        with patch('payments.views.Refunds.admin_refund_management.send_templated_email'):
            view_for_cleanup.clean_expired_unverified_refund_requests()

        # Test filtering by 'pending'
        request = self.factory.get(reverse('payments:admin_refund_management'), {'status': 'pending'})
        request.user = self.staff_user
        view = AdminRefundManagement()
        view.request = request
        with patch('payments.views.Refunds.admin_refund_management.send_templated_email'):
            queryset = view.get_queryset()

        self.assertEqual(len(queryset), 1)
        self.assertEqual(queryset.first(), self.req_pending_hire)

        # Test filtering by 'unverified' (should only show the new one after cleanup)
        request = self.factory.get(reverse('payments:admin_refund_management'), {'status': 'unverified'})
        request.user = self.staff_user
        view = AdminRefundManagement()
        view.request = request
        with patch('payments.views.Refunds.admin_refund_management.send_templated_email'):
            queryset = view.get_queryset()

        self.assertEqual(len(queryset), 1)
        self.assertEqual(queryset.first(), self.req_unverified_new)

        # Test filtering by 'refunded'
        request = self.factory.get(reverse('payments:admin_refund_management'), {'status': 'refunded'})
        request.user = self.staff_user
        view = AdminRefundManagement()
        view.request = request
        with patch('payments.views.Refunds.admin_refund_management.send_templated_email'):
            queryset = view.get_queryset()

        self.assertEqual(len(queryset), 1)
        self.assertEqual(queryset.first(), self.req_refunded_sales)


    def test_get_context_data(self):
        """
        Tests that status choices and current status are added to the context.
        Ensures self.object_list is populated before calling super().get_context_data.
        """
        # CORRECTED URL REVERSE for RequestFactory.get:
        request = self.factory.get(reverse('payments:admin_refund_management'), {'status': 'approved'})
        request.user = self.staff_user
        view = AdminRefundManagement()
        view.request = request # Set the request object on the view

        # Manually call get_queryset to populate self.object_list, simulating ListView's internal process
        # Patch send_templated_email during this call to prevent emails from being sent
        with patch('payments.views.Refunds.admin_refund_management.send_templated_email'):
            view.object_list = view.get_queryset() 

        context = view.get_context_data()

        self.assertIn('status_choices', context)
        self.assertIn('current_status', context)
        self.assertEqual(context['current_status'], 'approved')
        self.assertEqual(context['status_choices'], RefundRequest.STATUS_CHOICES)

        # Test default 'all' status
        # CORRECTED URL REVERSE for RequestFactory.get:
        request = self.factory.get(reverse('payments:admin_refund_management'))
        request.user = self.staff_user
        view = AdminRefundManagement()
        view.request = request
        
        with patch('payments.views.Refunds.admin_refund_management.send_templated_email'):
            view.object_list = view.get_queryset() 

        context = view.get_context_data()
        self.assertEqual(context['current_status'], 'all')

    def test_html_content_display(self):
        """
        Tests that the rendered HTML contains expected elements for different booking types.
        This requires rendering the template, which is usually done by the Django test client.
        """
        # Ensure cleanup runs before rendering HTML to reflect accurate state
        request_for_cleanup = self.factory.get(reverse('payments:admin_refund_management'))
        request_for_cleanup.user = self.staff_user
        view_for_cleanup = AdminRefundManagement()
        view_for_cleanup.request = request_for_cleanup
        with patch('payments.views.Refunds.admin_refund_management.send_templated_email'):
            view_for_cleanup.clean_expired_unverified_refund_requests()


        # CORRECTED URL REVERSE for client.get:
        response = self.client.get(reverse('payments:admin_refund_management'))
        self.assertEqual(response.status_code, 200)

        content = response.content.decode('utf-8')

        # Check for filtering options
        self.assertIn('<select name="status"', content)
        # Verify the "All" option is present and selected by default
        self.assertIn('<option value="all" selected>All</option>', content) 
        self.assertIn('<option value="pending">Pending Review</option>', content)
        self.assertIn('<option value="refunded">Refunded</option>', content)

        # Check for Hire Booking display
        self.assertIn(f'<td>Hire</td>', content)
        self.assertIn(f'<td>{self.req_pending_hire.hire_booking.booking_reference}</td>', content)
        self.assertIn(f'<td>{self.req_pending_hire.request_email}</td>', content)
        self.assertIn(f'<td>{self.req_pending_hire.amount_to_refund.quantize(Decimal("0.01"))}</td>', content)
        self.assertIn(f'<td>Pending Review</td>', content)

        # Check for Service Booking display
        self.assertIn(f'<td>Service</td>', content)
        self.assertIn(f'<td>{self.req_approved_service.service_booking.service_booking_reference}</td>', content)
        self.assertIn(f'<td>{self.req_approved_service.request_email}</td>', content)
        self.assertIn(f'<td>{self.req_approved_service.amount_to_refund.quantize(Decimal("0.01"))}</td>', content)
        self.assertIn(f'<td>Approved - Awaiting Refund</td>', content)

        # Check for Sales Booking display
        self.assertIn(f'<td>Sales</td>', content)
        self.assertIn(f'<td>{self.req_rejected_sales.sales_booking.sales_booking_reference}</td>', content)
        self.assertIn(f'<td>{self.req_rejected_sales.request_email}</td>', content)
        self.assertIn(f'<td>{self.req_rejected_sales.amount_to_refund.quantize(Decimal("0.01"))}</td>', content)
        self.assertIn(f'<td>Rejected</td>', content)
        
        # Check for the old unverified request being *deleted* from the display
        self.assertNotIn(f'{self.req_unverified_old.hire_booking.booking_reference}', content)
        self.assertNotIn(f'old_unverified@example.com', content)

        # Check for the new unverified request still being present
        self.assertIn(f'{self.req_unverified_new.service_booking.service_booking_reference}', content)
        self.assertIn(f'new_unverified@example.com', content)

        # Check for refunded sales booking
        self.assertIn(f'<td>{self.req_refunded_sales.sales_booking.sales_booking_reference}</td>', content)
        self.assertIn(f'<td>{self.req_refunded_sales.request_email}</td>', content)
        self.assertIn(f'<td>Refunded</td>', content)

        # Check for partially refunded hire booking
        self.assertIn(f'<td>{self.req_partially_refunded_hire.hire_booking.booking_reference}</td>', content)
        self.assertIn(f'<td>{self.req_partially_refunded_hire.request_email}</td>', content)
        self.assertIn(f'<td>Partially Refunded</td>', content)
