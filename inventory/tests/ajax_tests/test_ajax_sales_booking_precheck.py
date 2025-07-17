import json
from django.test import TestCase, RequestFactory
from django.urls import reverse
from unittest.mock import patch, MagicMock
from inventory.ajax.ajax_sales_booking_precheck import sales_booking_precheck_ajax
from users.tests.test_helpers.model_factories import UserFactory

class SalesBookingPrecheckAjaxTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin_user = UserFactory(is_staff=True)
        self.non_admin_user = UserFactory()

    def test_permission_denied_for_non_staff_user(self):
        request = self.factory.post(reverse('inventory:admin_api_sales_booking_precheck'))
        request.user = self.non_admin_user
        response = sales_booking_precheck_ajax(request)
        self.assertEqual(response.status_code, 403)
        data = json.loads(response.content)
        self.assertEqual(data, {"status": "error", "message": "Admin access required."})

    @patch('inventory.ajax.ajax_sales_booking_precheck.AdminSalesBookingForm')
    def test_form_is_valid_no_warnings(self, MockAdminSalesBookingForm):
        mock_form_instance = MockAdminSalesBookingForm.return_value
        mock_form_instance.is_valid.return_value = True
        mock_form_instance.get_warnings.return_value = []

        request = self.factory.post(reverse('inventory:admin_api_sales_booking_precheck'), data={})
        request.user = self.admin_user
        response = sales_booking_precheck_ajax(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['errors'], {})
        self.assertEqual(data['warnings'], [])

    @patch('inventory.ajax.ajax_sales_booking_precheck.AdminSalesBookingForm')
    def test_form_is_valid_with_warnings(self, MockAdminSalesBookingForm):
        mock_form_instance = MockAdminSalesBookingForm.return_value
        mock_form_instance.is_valid.return_value = True
        mock_form_instance.get_warnings.return_value = ['Warning 1', 'Warning 2']

        request = self.factory.post(reverse('inventory:admin_api_sales_booking_precheck'), data={})
        request.user = self.admin_user
        response = sales_booking_precheck_ajax(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'warnings')
        self.assertEqual(data['errors'], {})
        self.assertEqual(data['warnings'], ['Warning 1', 'Warning 2'])

    @patch('inventory.ajax.ajax_sales_booking_precheck.AdminSalesBookingForm')
    def test_form_is_invalid(self, MockAdminSalesBookingForm):
        mock_form_instance = MockAdminSalesBookingForm.return_value
        mock_form_instance.is_valid.return_value = False
        mock_form_instance.errors = {'field1': ['Error 1'], '__all__': ['Non-field error']}

        request = self.factory.post(reverse('inventory:admin_api_sales_booking_precheck'), data={})
        request.user = self.admin_user
        response = sales_booking_precheck_ajax(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'errors')
        self.assertEqual(data['errors'], {'field1': ['Error 1'], '__all__': ['Non-field error']})
        self.assertEqual(data['warnings'], [])