from django.test import TestCase
from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone
import datetime

from service.forms import (
    ServiceDetailsForm,
    CustomerMotorcycleForm,
    ServiceBookingUserForm,
    ExistingCustomerMotorcycleForm,
)
from service.models import ServiceType, CustomerMotorcycle, ServiceBooking
from inventory.models import Motorcycle

User = get_user_model()

class ServiceDetailsFormTests(TestCase):

    def setUp(self):
        self.service_type = ServiceType.objects.create(
            name="Oil Change",
            description="Standard oil and filter change.",
            estimated_duration=datetime.timedelta(hours=1),
            base_price=50.00,
            is_active=True
        )

    # Test ServiceDetailsForm with valid data
    def test_service_details_form_valid_data(self):
        future_datetime = timezone.now() + datetime.timedelta(days=1)
        future_datetime = future_datetime.replace(second=0, microsecond=0)

        form_data = {
            'service_type': self.service_type.id,
            'appointment_datetime': future_datetime.strftime('%Y-%m-%dT%H:%M'),
            # Removed 'booking_comments' from here
        }
        form = ServiceDetailsForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['service_type'], self.service_type)
        self.assertIsInstance(form.cleaned_data['appointment_datetime'], datetime.datetime)
        self.assertAlmostEqual(form.cleaned_data['appointment_datetime'], future_datetime, delta=datetime.timedelta(seconds=5))
        # Removed assertion for booking_comments

    # Test ServiceDetailsForm with invalid data
    def test_service_details_form_invalid_data(self):
        form_data = {
            'service_type': '',
            'appointment_datetime': 'invalid-date',
            # Removed 'booking_comments' from here
        }
        form = ServiceDetailsForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('service_type', form.errors)
        self.assertIn('appointment_datetime', form.errors)

    # Removed test_service_details_form_no_comments

    # Test that ServiceDetailsForm uses the correct widgets
    def test_service_details_form_widget_types(self):
        form = ServiceDetailsForm()
        self.assertIsInstance(form.fields['service_type'].widget, forms.Select)
        self.assertIsInstance(form.fields['appointment_datetime'].widget, forms.DateTimeInput)
        widget_attrs = form.fields['appointment_datetime'].widget.attrs
        self.assertIn('class', widget_attrs)
        self.assertEqual(widget_attrs['class'], 'form-control')
        # Removed assertion for booking_comments widget


class ServiceBookingUserFormTests(TestCase):

    # Test ServiceBookingUserForm with valid data
    def test_service_booking_user_form_valid_data(self):
        form_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@example.com',
            'phone_number': '123-456-7890',
            'preferred_contact': 'email',
            'booking_comments': 'Please be careful with the fairings.', # Added booking_comments
        }
        form = ServiceBookingUserForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['first_name'], 'John')
        self.assertEqual(form.cleaned_data['last_name'], 'Doe')
        self.assertEqual(form.cleaned_data['email'], 'john.doe@example.com')
        self.assertEqual(form.cleaned_data['phone_number'], '123-456-7890')
        self.assertEqual(form.cleaned_data['preferred_contact'], 'email')
        self.assertEqual(form.cleaned_data['booking_comments'], 'Please be careful with the fairings.') # Added assertion

    # Test ServiceBookingUserForm with invalid data
    def test_service_booking_user_form_invalid_data(self):
        form_data = {
            'first_name': '',
            'last_name': 'Doe',
            'email': 'invalid-email',
            'phone_number': '123-456-7890',
            'preferred_contact': 'carrier_pigeon',
            'booking_comments': 'Test comments', # Added booking_comments
        }
        form = ServiceBookingUserForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('first_name', form.errors)
        self.assertIn('email', form.errors)
        self.assertIn('preferred_contact', form.errors)
        # No specific invalid data for booking_comments in this example, but you can add if needed

    # Test ServiceBookingUserForm when phone number is not provided
    def test_service_booking_user_form_optional_phone(self):
        form_data = {
            'first_name': 'Jane',
            'last_name': 'Smith',
            'email': 'jane.smith@example.com',
            'preferred_contact': 'phone',
            'booking_comments': '', # Added booking_comments as optional
        }
        form = ServiceBookingUserForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['first_name'], 'Jane')
        self.assertEqual(form.cleaned_data['last_name'], 'Smith')
        self.assertEqual(form.cleaned_data['email'], 'jane.smith@example.com')
        self.assertEqual(form.cleaned_data['preferred_contact'], 'phone')
        self.assertEqual(form.cleaned_data['phone_number'], '')
        self.assertEqual(form.cleaned_data['booking_comments'], '') # Added assertion for optional field

    # Test that preferred_contact defaults to 'email'
    def test_service_booking_user_form_preferred_contact_initial(self):
        form = ServiceBookingUserForm()
        self.assertEqual(form.fields['preferred_contact'].initial, 'email')
        # No change needed for booking_comments default as it's not required

    # Test that ServiceBookingUserForm uses the correct widgets
    def test_service_booking_user_form_widget_types(self):
        form = ServiceBookingUserForm()
        self.assertIsInstance(form.fields['first_name'].widget, forms.TextInput)
        self.assertIsInstance(form.fields['last_name'].widget, forms.TextInput)
        self.assertIsInstance(form.fields['email'].widget, forms.EmailInput)
        self.assertIsInstance(form.fields['phone_number'].widget, forms.TextInput)
        self.assertIsInstance(form.fields['preferred_contact'].widget, forms.RadioSelect)
        self.assertIsInstance(form.fields['booking_comments'].widget, forms.Textarea) # Added assertion for booking_comments
class ServiceBookingUserFormTests(TestCase):

    # Test ServiceBookingUserForm with valid data
    def test_service_booking_user_form_valid_data(self):
        form_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@example.com',
            'phone_number': '123-456-7890',
            'preferred_contact': 'email',
        }
        form = ServiceBookingUserForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['first_name'], 'John')
        self.assertEqual(form.cleaned_data['last_name'], 'Doe')
        self.assertEqual(form.cleaned_data['email'], 'john.doe@example.com')
        self.assertEqual(form.cleaned_data['phone_number'], '123-456-7890')
        self.assertEqual(form.cleaned_data['preferred_contact'], 'email')

    # Test ServiceBookingUserForm with invalid data
    def test_service_booking_user_form_invalid_data(self):
        form_data = {
            'first_name': '',
            'last_name': 'Doe',
            'email': 'invalid-email',
            'phone_number': '123-456-7890',
            'preferred_contact': 'carrier_pigeon',
        }
        form = ServiceBookingUserForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('first_name', form.errors)
        self.assertIn('email', form.errors)
        self.assertIn('preferred_contact', form.errors)

    # Test ServiceBookingUserForm when phone number is not provided
    def test_service_booking_user_form_optional_phone(self):
        form_data = {
            'first_name': 'Jane',
            'last_name': 'Smith',
            'email': 'jane.smith@example.com',
            'preferred_contact': 'phone',
        }
        form = ServiceBookingUserForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['first_name'], 'Jane')
        self.assertEqual(form.cleaned_data['last_name'], 'Smith')
        self.assertEqual(form.cleaned_data['email'], 'jane.smith@example.com')
        self.assertEqual(form.cleaned_data['preferred_contact'], 'phone')
        self.assertEqual(form.cleaned_data['phone_number'], '')

    # Test that preferred_contact defaults to 'email'
    def test_service_booking_user_form_preferred_contact_initial(self):
        form = ServiceBookingUserForm()
        self.assertEqual(form.fields['preferred_contact'].initial, 'email')

    # Test that ServiceBookingUserForm uses the correct widgets
    def test_service_booking_user_form_widget_types(self):
        form = ServiceBookingUserForm()
        self.assertIsInstance(form.fields['first_name'].widget, forms.TextInput)
        self.assertIsInstance(form.fields['last_name'].widget, forms.TextInput)
        self.assertIsInstance(form.fields['email'].widget, forms.EmailInput)
        self.assertIsInstance(form.fields['phone_number'].widget, forms.TextInput)
        self.assertIsInstance(form.fields['preferred_contact'].widget, forms.RadioSelect)


class ExistingCustomerMotorcycleFormTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.other_user = User.objects.create_user(username='otheruser', password='password')

        self.motorcycle1 = CustomerMotorcycle.objects.create(
            owner=self.user,
            make='Honda',
            model='CBR500R',
            year=2020,
            rego='TEST1',
            transmission='manual'
        )
        self.motorcycle2 = CustomerMotorcycle.objects.create(
            owner=self.user,
            make='Yamaha',
            model='MT-07',
            year=2022,
            rego='TEST2',
            transmission='manual'
        )
        self.other_user_motorcycle = CustomerMotorcycle.objects.create(
            owner=self.other_user,
            make='Suzuki',
            model='SV650',
            year=2021,
            rego='OTHER1',
            transmission='manual'
        )

    # Test that the queryset is filtered by the user
    def test_existing_customer_motorcycle_form_queryset(self):
        form = ExistingCustomerMotorcycleForm(user=self.user)
        form_queryset = form.fields['motorcycle'].queryset
        self.assertEqual(form_queryset.count(), 2)
        self.assertIn(self.motorcycle1, form_queryset)
        self.assertIn(self.motorcycle2, form_queryset)
        self.assertNotIn(self.other_user_motorcycle, form_queryset)

    # Test selecting an existing motorcycle
    def test_existing_customer_motorcycle_form_valid_selection(self):
        form_data = {
            'motorcycle': self.motorcycle1.id,
        }
        form = ExistingCustomerMotorcycleForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['motorcycle'], self.motorcycle1)

    # Test selecting a motorcycle not owned by the user
    def test_existing_customer_motorcycle_form_invalid_selection(self):
        form_data = {
            'motorcycle': self.other_user_motorcycle.id,
        }
        form = ExistingCustomerMotorcycleForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('motorcycle', form.errors)

    # Test the form behavior when no user is provided (e.g., anonymous user)
    def test_existing_customer_motorcycle_form_no_user(self):
        form = ExistingCustomerMotorcycleForm()
        form_queryset = form.fields['motorcycle'].queryset
        self.assertEqual(form_queryset.count(), 0)

    # Test that ExistingCustomerMotorcycleForm uses the correct widgets
    def test_existing_customer_motorcycle_form_widget_types(self):
        form = ExistingCustomerMotorcycleForm(user=self.user)
        self.assertIsInstance(form.fields['motorcycle'].widget, forms.Select)