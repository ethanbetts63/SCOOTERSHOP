from django.test import TestCase
from django.urls import reverse
from payments.models import RefundPolicySettings
from payments.tests.test_helpers.model_factories import UserFactory, RefundPolicySettingsFactory
from django.contrib.messages import get_messages
from decimal import Decimal

class AdminRefundSettingsViewTest(TestCase):

    def setUp(self):
        self.admin_user = UserFactory(is_staff=True)
        self.client.force_login(self.admin_user)
        self.refund_settings = RefundPolicySettingsFactory()

    def test_get_admin_refund_settings_view(self):
        response = self.client.get(reverse('payments:admin_refund_settings'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/admin_refund_settings.html')
        self.assertIn('form', response.context)
        self.assertEqual(response.context['form'].instance, self.refund_settings)

    def test_post_admin_refund_settings_view_success(self):
        data = {
            'cancellation_full_payment_full_refund_days': 10,
            'cancellation_full_payment_partial_refund_days': 5,
            'cancellation_full_payment_partial_refund_percentage': Decimal('50.00'),
            'cancellation_full_payment_minimal_refund_days': 1,
            'cancellation_full_payment_minimal_refund_percentage': Decimal('10.00'),
            'cancellation_deposit_full_refund_days': 7,
            'cancellation_deposit_partial_refund_days': 3,
            'cancellation_deposit_partial_refund_percentage': Decimal('25.00'),
            'cancellation_deposit_minimal_refund_days': 0,
            'cancellation_deposit_minimal_refund_percentage': Decimal('0.00'),
            'sales_enable_deposit_refund_grace_period': True,
            'sales_deposit_refund_grace_period_hours': 24,
            'sales_enable_deposit_refund': True,
            'refund_deducts_stripe_fee_policy': True,
            'stripe_fee_percentage_domestic': Decimal('0.017'),
            'stripe_fee_fixed_domestic': Decimal('0.30'),
            'stripe_fee_percentage_international': Decimal('0.035'),
            'stripe_fee_fixed_international': Decimal('0.40'),
            'refund_policy_settings_submit': '',
        }
        response = self.client.post(reverse('payments:admin_refund_settings'), data=data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('payments:admin_refund_settings'))
        self.refund_settings.refresh_from_db()
        self.assertEqual(self.refund_settings.cancellation_full_payment_full_refund_days, 10)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'Refund Policy settings updated successfully!')

    def test_post_admin_refund_settings_view_invalid(self):
        data = {
            'cancellation_full_payment_full_refund_days': -1, # Invalid data
            'refund_policy_settings_submit': '',
        }
        response = self.client.post(reverse('payments:admin_refund_settings'), data=data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/admin_refund_settings.html')
        self.assertIn('form', response.context)
        self.assertFalse(response.context['form'].is_valid())
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'There was an error updating refund policy settings. Please correct the errors below.')

    def test_admin_required_mixin(self):
        self.client.logout()
        response = self.client.get(reverse('payments:admin_refund_settings'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('users:login') + '?next=' + reverse('payments:admin_refund_settings'))