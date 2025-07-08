
from django.test import TestCase
from inventory.forms import AdminSalesProfileForm
from inventory.tests.test_helpers.model_factories import SalesProfileFactory, UserFactory
from django.core.exceptions import ValidationError

class AdminSalesProfileFormTest(TestCase):

    def setUp(self):
        self.user = UserFactory()
        self.sales_profile = SalesProfileFactory(user=self.user)

    def test_valid_form_with_linked_user(self):
        # Create a new user that is not linked to any existing sales profile
        new_user = UserFactory()
        form = AdminSalesProfileForm(data={
            'user': new_user.pk,
            'name': 'Test Name',
            'email': 'test@example.com',
            'phone_number': '1234567890',
            'address_line_1': '123 Test St',
            'city': 'Test City',
            'state': 'TS',
            'post_code': '12345',
            'country': 'AU',
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_valid_form_without_linked_user(self):
        form = AdminSalesProfileForm(data={
            'user': '',
            'name': 'Another Name',
            'email': 'another@example.com',
            'phone_number': '0987654321',
            'address_line_1': '456 Other St',
            'city': 'Other City',
            'state': 'OT',
            'post_code': '54321',
            'country': 'AU',
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_clean_user_already_linked_to_another_profile(self):
        another_user = UserFactory()
        SalesProfileFactory(user=another_user)
        form = AdminSalesProfileForm(data={
            'user': another_user.pk,
            'name': 'Test Name',
            'email': 'test@example.com',
            'phone_number': '1234567890',
            'address_line_1': '123 Test St',
            'city': 'Test City',
            'state': 'TS',
            'post_code': '12345',
            'country': 'AU',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('user', form.errors)
        self.assertEqual(form.errors['user'], [f'This user ({another_user.username}) is already linked to another Sales Profile.'])

    def test_clean_user_already_linked_to_current_profile(self):
        form = AdminSalesProfileForm(instance=self.sales_profile, data={
            'user': self.user.pk,
            'name': self.sales_profile.name,
            'email': self.sales_profile.email,
            'phone_number': self.sales_profile.phone_number,
            'address_line_1': self.sales_profile.address_line_1,
            'city': self.sales_profile.city,
            'state': self.sales_profile.state,
            'post_code': self.sales_profile.post_code,
            'country': self.sales_profile.country,
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_missing_required_fields_without_linked_user(self):
        form = AdminSalesProfileForm(data={
            'user': '',
            'name': '',
            'email': '',
            'phone_number': '',
            'address_line_1': '123 Test St',
            'city': 'Test City',
            'state': 'TS',
            'post_code': '12345',
            'country': 'AU',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
        self.assertIn('Full Name is required if no user account is linked.', form.errors['name'])
        self.assertIn('email', form.errors)
        self.assertIn('Email Address is required if no user account is linked.', form.errors['email'])
        self.assertIn('phone_number', form.errors)
        self.assertIn('Phone Number is required if no user account is linked.', form.errors['phone_number'])
