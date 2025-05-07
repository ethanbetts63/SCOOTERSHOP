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
    BaseAdminServiceBookingForm,
    AdminAnonBookingForm,
    AdminUserBookingForm,
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
        }
        form = ServiceDetailsForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['service_type'], self.service_type)
        self.assertIsInstance(form.cleaned_data['appointment_datetime'], datetime.datetime)
        self.assertAlmostEqual(form.cleaned_data['appointment_datetime'], future_datetime, delta=datetime.timedelta(seconds=5))

    # Test ServiceDetailsForm with invalid data
    def test_service_details_form_invalid_data(self):
        form_data = {
            'service_type': '',
            'appointment_datetime': 'invalid-date',
        }
        form = ServiceDetailsForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('service_type', form.errors)
        self.assertIn('appointment_datetime', form.errors)

    # Test that ServiceDetailsForm uses the correct widgets
    def test_service_details_form_widget_types(self):
        form = ServiceDetailsForm()
        self.assertIsInstance(form.fields['service_type'].widget, forms.Select)
        self.assertIsInstance(form.fields['appointment_datetime'].widget, forms.DateTimeInput)
        widget_attrs = form.fields['appointment_datetime'].widget.attrs
        self.assertIn('class', widget_attrs)
        self.assertEqual(widget_attrs['class'], 'form-control')


class ServiceBookingUserFormTests(TestCase):

    # Test ServiceBookingUserForm with valid data
    def test_service_booking_user_form_valid_data(self):
        form_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@example.com',
            'phone_number': '123-456-7890',
            'preferred_contact': 'email',
            'booking_comments': 'Please be careful with the fairings.',
        }
        form = ServiceBookingUserForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['first_name'], 'John')
        self.assertEqual(form.cleaned_data['last_name'], 'Doe')
        self.assertEqual(form.cleaned_data['email'], 'john.doe@example.com')
        self.assertEqual(form.cleaned_data['phone_number'], '123-456-7890')
        self.assertEqual(form.cleaned_data['preferred_contact'], 'email')
        self.assertEqual(form.cleaned_data['booking_comments'], 'Please be careful with the fairings.')

    # Test ServiceBookingUserForm with invalid data
    def test_service_booking_user_form_invalid_data(self):
        form_data = {
            'first_name': '',
            'last_name': 'Doe',
            'email': 'invalid-email',
            'phone_number': '123-456-7890',
            'preferred_contact': 'carrier_pigeon',
            'booking_comments': 'Test comments',
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
            'booking_comments': '',
        }
        form = ServiceBookingUserForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['first_name'], 'Jane')
        self.assertEqual(form.cleaned_data['last_name'], 'Smith')
        self.assertEqual(form.cleaned_data['email'], 'jane.smith@example.com')
        self.assertEqual(form.cleaned_data['preferred_contact'], 'phone')
        self.assertEqual(form.cleaned_data['phone_number'], '')
        self.assertEqual(form.cleaned_data['booking_comments'], '')

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
        self.assertIsInstance(form.fields['booking_comments'].widget, forms.Textarea)


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
        self.assertEqual(form_queryset.count(), 0) # Changed from form_queryset to queryset - assume it's a typo in original test

    # Test that ExistingCustomerMotorcycleForm uses the correct widgets
    def test_existing_customer_motorcycle_form_widget_types(self):
        form = ExistingCustomerMotorcycleForm(user=self.user)
        self.assertIsInstance(form.fields['motorcycle'].widget, forms.Select)


class BaseAdminServiceBookingFormTests(TestCase):

    def setUp(self):
        self.service_type = ServiceType.objects.create(
            name="Annual Service",
            description="Full annual service.",
            estimated_duration=datetime.timedelta(hours=3),
            base_price=200.00,
            is_active=True
        )
        self.inactive_service_type = ServiceType.objects.create(
            name="Inactive Service",
            description="This service is inactive.",
            estimated_duration=datetime.timedelta(hours=1),
            base_price=100.00,
            is_active=False
        )

    # Test BaseAdminServiceBookingForm with valid data (removed preferred_contact)
    def test_base_admin_form_valid_data(self):
        future_datetime = timezone.now() + datetime.timedelta(days=2)
        future_datetime = future_datetime.replace(second=0, microsecond=0)

        form_data = {
            'service_type': self.service_type.id,
            'appointment_datetime': future_datetime.strftime('%Y-%m-%dT%H:%M'),
            'booking_comments': 'Please call before starting work.',
        }
        form = BaseAdminServiceBookingForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['service_type'], self.service_type)
        self.assertIsInstance(form.cleaned_data['appointment_datetime'], datetime.datetime)
        self.assertAlmostEqual(form.cleaned_data['appointment_datetime'], future_datetime, delta=datetime.timedelta(seconds=5))
        self.assertEqual(form.cleaned_data['booking_comments'], 'Please call before starting work.')

    # Test BaseAdminServiceBookingForm with invalid data (removed preferred_contact)
    def test_base_admin_form_invalid_data(self):
        form_data = {
            'service_type': '',
            'appointment_datetime': 'not a date',
            'booking_comments': 'Some comments',
        }
        form = BaseAdminServiceBookingForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('service_type', form.errors)
        self.assertIn('appointment_datetime', form.errors)


    # Test that the service_type queryset only includes active services
    def test_base_admin_form_service_type_queryset(self):
        form = BaseAdminServiceBookingForm()
        queryset = form.fields['service_type'].queryset
        self.assertIn(self.service_type, queryset)
        self.assertNotIn(self.inactive_service_type, queryset)

    # Test that BaseAdminServiceBookingForm uses the correct widgets (removed preferred_contact)
    def test_base_admin_form_widget_types(self):
        form = BaseAdminServiceBookingForm()
        self.assertIsInstance(form.fields['service_type'].widget, forms.Select)
        self.assertIsInstance(form.fields['appointment_datetime'].widget, forms.DateTimeInput)
        self.assertIsInstance(form.fields['booking_comments'].widget, forms.Textarea)


class AdminAnonBookingFormTests(TestCase):

    def setUp(self):
        self.service_type = ServiceType.objects.create(
            name="Tyre Change",
            description="Replace front and rear tyres.",
            estimated_duration=datetime.timedelta(hours=1, minutes=30),
            base_price=80.00,
            is_active=True
        )

    # Test AdminAnonBookingForm with valid data (updated for new fields and required status)
    def test_anon_booking_form_valid_data(self):
        future_datetime = timezone.now() + datetime.timedelta(days=3)
        future_datetime = future_datetime.replace(second=0, microsecond=0)

        form_data = {
            'service_type': self.service_type.id,
            'appointment_datetime': future_datetime.strftime('%Y-%m-%dT%H:%M'),
            'booking_comments': 'Bring my old tyres back.',
            'one_off_first_name': 'Anonymous',
            'one_off_last_name': 'Customer',
            'one_off_email': 'anon.customer@example.com',
            'one_off_phone_number': '0987654321',
            'anon_customer_address': '123 Anonymity Lane', # Added
            'anon_vehicle_make': 'Kawasaki',
            'anon_vehicle_model': 'Ninja 400',
            'anon_vehicle_year': 2023,
            'anon_vehicle_rego': 'ANON1',
            'anon_vehicle_vin_number': 'VINANON456', # Added
            'anon_vehicle_odometer': 5000,
            'anon_vehicle_transmission': 'manual',
            'anon_engine_number': 'ENGANON789', # Added
        }
        form = AdminAnonBookingForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['service_type'], self.service_type)
        self.assertIsInstance(form.cleaned_data['appointment_datetime'], datetime.datetime)
        self.assertAlmostEqual(form.cleaned_data['appointment_datetime'], future_datetime, delta=datetime.timedelta(seconds=5))
        self.assertEqual(form.cleaned_data['booking_comments'], 'Bring my old tyres back.')
        self.assertEqual(form.cleaned_data['one_off_first_name'], 'Anonymous')
        self.assertEqual(form.cleaned_data['one_off_last_name'], 'Customer')
        self.assertEqual(form.cleaned_data['one_off_email'], 'anon.customer@example.com')
        self.assertEqual(form.cleaned_data['one_off_phone_number'], '0987654321')
        self.assertEqual(form.cleaned_data['anon_customer_address'], '123 Anonymity Lane') # Assert added field
        self.assertEqual(form.cleaned_data['anon_vehicle_make'], 'Kawasaki')
        self.assertEqual(form.cleaned_data['anon_vehicle_model'], 'Ninja 400')
        self.assertEqual(form.cleaned_data['anon_vehicle_year'], 2023)
        self.assertEqual(form.cleaned_data['anon_vehicle_rego'], 'ANON1')
        self.assertEqual(form.cleaned_data['anon_vehicle_vin_number'], 'VINANON456') # Assert added field
        self.assertEqual(form.cleaned_data['anon_vehicle_odometer'], 5000)
        self.assertEqual(form.cleaned_data['anon_vehicle_transmission'], 'manual')
        self.assertEqual(form.cleaned_data['anon_engine_number'], 'ENGANON789') # Assert added field


    # Test AdminAnonBookingForm with missing required data (updated for new required fields)
    def test_anon_booking_form_missing_required_data(self):
        future_datetime = timezone.now() + datetime.timedelta(days=3)
        future_datetime = future_datetime.replace(second=0, microsecond=0)

        form_data = {
            'service_type': self.service_type.id,
            'appointment_datetime': future_datetime.strftime('%Y-%m-%dT%H:%M'),
            'one_off_email': 'anon.customer@example.com', # Now optional
            'one_off_phone_number': '0987654321', # Now optional
            'anon_customer_address': '123 Anonymity Lane', # Now optional
            'anon_vehicle_year': 2023, # Now optional
            'anon_vehicle_rego': 'ANON1', # Now optional
            'anon_vehicle_vin_number': 'VINANON456', # Now optional
            'anon_vehicle_odometer': 5000, # Now optional
            'anon_vehicle_transmission': 'manual', # Now optional
            'anon_engine_number': 'ENGANON789', # Now optional
            'booking_comments': 'Test comments', # Still optional
            # Missing one_off_first_name, one_off_last_name, anon_vehicle_make, anon_vehicle_model
        }
        form = AdminAnonBookingForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('one_off_first_name', form.errors)
        self.assertIn('one_off_last_name', form.errors)
        self.assertIn('anon_vehicle_make', form.errors)
        self.assertIn('anon_vehicle_model', form.errors)
        # Ensure now optional fields do NOT cause errors
        self.assertNotIn('one_off_email', form.errors)
        self.assertNotIn('one_off_phone_number', form.errors)
        self.assertNotIn('anon_customer_address', form.errors)
        self.assertNotIn('anon_vehicle_year', form.errors)
        self.assertNotIn('anon_vehicle_rego', form.errors)
        self.assertNotIn('anon_vehicle_vin_number', form.errors)
        self.assertNotIn('anon_vehicle_odometer', form.errors)
        self.assertNotIn('anon_vehicle_transmission', form.errors)
        self.assertNotIn('anon_engine_number', form.errors)
        self.assertNotIn('booking_comments', form.errors)


    # Test AdminAnonBookingForm with invalid email (email is now optional, so invalid format is only an error if provided)
    def test_anon_booking_form_invalid_email(self):
        future_datetime = timezone.now() + datetime.timedelta(days=3)
        future_datetime = future_datetime.replace(second=0, microsecond=0)

        form_data = {
            'service_type': self.service_type.id,
            'appointment_datetime': future_datetime.strftime('%Y-%m-%dT%H:%M'),
            'one_off_first_name': 'Anonymous',
            'one_off_last_name': 'Customer',
            'one_off_email': 'invalid-email', # Invalid format
            'anon_vehicle_make': 'Kawasaki',
            'anon_vehicle_model': 'Ninja 400',
            # Optional fields can be missing or empty
        }
        form = AdminAnonBookingForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('one_off_email', form.errors)


    # Test AdminAnonBookingForm with optional fields empty (updated for new optional fields)
    def test_anon_booking_form_optional_fields_empty(self):
        future_datetime = timezone.now() + datetime.timedelta(days=3)
        future_datetime = future_datetime.replace(second=0, microsecond=0)

        form_data = {
            'service_type': self.service_type.id,
            'appointment_datetime': future_datetime.strftime('%Y-%m-%dT%H:%M'),
            'booking_comments': '', # Optional
            'one_off_first_name': 'Anonymous',
            'one_off_last_name': 'Customer',
            'one_off_email': '', # Optional
            'one_off_phone_number': '', # Optional
            'anon_customer_address': '', # Added - Optional
            'anon_vehicle_make': 'Kawasaki', # Required
            'anon_vehicle_model': 'Ninja 400', # Required
            'anon_vehicle_year': '', # Optional (empty string for NumberInput)
            'anon_vehicle_rego': '', # Optional
            'anon_vehicle_vin_number': '', # Added - Optional
            'anon_vehicle_odometer': '', # Optional (empty string for NumberInput)
            'anon_vehicle_transmission': '', # Optional
            'anon_engine_number': '', # Added - Optional
        }
        form = AdminAnonBookingForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['booking_comments'], '')
        self.assertEqual(form.cleaned_data['one_off_email'], '') # Assert optional
        self.assertEqual(form.cleaned_data['one_off_phone_number'], '') # Assert optional
        self.assertEqual(form.cleaned_data['anon_customer_address'], '') # Assert added optional
        # Note: IntegerFields return None when empty
        self.assertIsNone(form.cleaned_data['anon_vehicle_year']) # Assert optional
        self.assertEqual(form.cleaned_data['anon_vehicle_rego'], '') # Assert optional
        self.assertEqual(form.cleaned_data['anon_vehicle_vin_number'], '') # Assert added optional
        self.assertIsNone(form.cleaned_data['anon_vehicle_odometer']) # Assert optional
        self.assertEqual(form.cleaned_data['anon_vehicle_transmission'], '') # Assert optional
        self.assertEqual(form.cleaned_data['anon_engine_number'], '') # Assert added optional


    # Test that AdminAnonBookingForm uses the correct widgets (updated for new fields and removed preferred_contact)
    def test_anon_booking_form_widget_types(self):
        form = AdminAnonBookingForm()
        self.assertIsInstance(form.fields['service_type'].widget, forms.Select)
        self.assertIsInstance(form.fields['appointment_datetime'].widget, forms.DateTimeInput)
        self.assertIsInstance(form.fields['booking_comments'].widget, forms.Textarea)
        self.assertIsInstance(form.fields['one_off_first_name'].widget, forms.TextInput)
        self.assertIsInstance(form.fields['one_off_last_name'].widget, forms.TextInput)
        self.assertIsInstance(form.fields['one_off_email'].widget, forms.EmailInput)
        self.assertIsInstance(form.fields['one_off_phone_number'].widget, forms.TextInput)
        self.assertIsInstance(form.fields['anon_customer_address'].widget, forms.Textarea) # Added assertion
        self.assertIsInstance(form.fields['anon_vehicle_make'].widget, forms.TextInput)
        self.assertIsInstance(form.fields['anon_vehicle_model'].widget, forms.TextInput)
        self.assertIsInstance(form.fields['anon_vehicle_year'].widget, forms.NumberInput)
        self.assertIsInstance(form.fields['anon_vehicle_rego'].widget, forms.TextInput)
        self.assertIsInstance(form.fields['anon_vehicle_vin_number'].widget, forms.TextInput) # Added assertion
        self.assertIsInstance(form.fields['anon_vehicle_odometer'].widget, forms.NumberInput)
        self.assertIsInstance(form.fields['anon_vehicle_transmission'].widget, forms.Select)
        self.assertIsInstance(form.fields['anon_engine_number'].widget, forms.TextInput) # Added assertion


class AdminUserBookingFormTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password', first_name='Test', last_name='User', email='testuser@example.com', phone_number='1112223333')
        self.other_user = User.objects.create_user(username='otheruser', password='password')
        self.service_type = ServiceType.objects.create(
            name="Major Service",
            description="Major service including valve clearance.",
            estimated_duration=datetime.timedelta(hours=5),
            base_price=400.00,
            is_active=True
        )
        self.motorcycle1 = CustomerMotorcycle.objects.create(
            owner=self.user,
            make='Honda',
            model='CBR600RR',
            year=2018,
            rego='USER1',
            transmission='manual'
        )
        self.motorcycle2 = CustomerMotorcycle.objects.create(
            owner=self.user,
            make='Suzuki',
            model='GSX-R750',
            year=2019,
            rego='USER2',
            transmission='manual'
        )
        self.other_user_motorcycle = CustomerMotorcycle.objects.create(
            owner=self.other_user,
            make='Kawasaki',
            model='ZX-6R',
            year=2020,
            rego='OTHER2',
            transmission='manual'
        )

    # Test AdminUserBookingForm with valid data - existing motorcycle (removed preferred_contact from base form)
    def test_admin_user_booking_form_valid_existing_motorcycle(self):
        future_datetime = timezone.now() + datetime.timedelta(days=4)
        future_datetime = future_datetime.replace(second=0, microsecond=0)

        form_data = {
            'service_type': self.service_type.id,
            'appointment_datetime': future_datetime.strftime('%Y-%m-%dT%H:%M'),
            'booking_comments': 'Check brakes.',
            'user': self.user.id,
            'bike_selection_type': 'existing',
            'existing_motorcycle': self.motorcycle1.id,
            # New bike fields should be empty
            'new_bike_make': '',
            'new_bike_model': '',
            'new_bike_year': '',
            'new_bike_rego': '',
            'new_bike_vin_number': '',
            'new_bike_odometer': '',
            'new_bike_transmission': '',
        }
        form = AdminUserBookingForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['service_type'], self.service_type)
        self.assertIsInstance(form.cleaned_data['appointment_datetime'], datetime.datetime)
        self.assertAlmostEqual(form.cleaned_data['appointment_datetime'], future_datetime, delta=datetime.timedelta(seconds=5))
        self.assertEqual(form.cleaned_data['booking_comments'], 'Check brakes.')
        self.assertEqual(form.cleaned_data['user'], self.user)
        self.assertEqual(form.cleaned_data['bike_selection_type'], 'existing')
        self.assertEqual(form.cleaned_data['existing_motorcycle'], self.motorcycle1)
        # Assert new bike fields are None or empty
        self.assertEqual(form.cleaned_data['new_bike_make'], '')
        self.assertEqual(form.cleaned_data['new_bike_model'], '')
        self.assertIsNone(form.cleaned_data['new_bike_year'])
        self.assertEqual(form.cleaned_data['new_bike_rego'], '')
        self.assertEqual(form.cleaned_data['new_bike_vin_number'], '')
        self.assertIsNone(form.cleaned_data['new_bike_odometer'])
        self.assertEqual(form.cleaned_data['new_bike_transmission'], '')


    # Test AdminUserBookingForm with valid data - new motorcycle (removed preferred_contact from base form)
    def test_admin_user_booking_form_valid_new_motorcycle(self):
        future_datetime = timezone.now() + datetime.timedelta(days=5)
        future_datetime = future_datetime.replace(second=0, microsecond=0)

        form_data = {
            'service_type': self.service_type.id,
            'appointment_datetime': future_datetime.strftime('%Y-%m-%dT%H:%M'),
            'booking_comments': 'First service.',
            'user': self.user.id,
            'bike_selection_type': 'new',
            'existing_motorcycle': '', # Existing motorcycle should be empty
            'new_bike_make': 'BMW',
            'new_bike_model': 'S1000RR',
            'new_bike_year': 2024,
            'new_bike_rego': 'NEW1',
            'new_bike_vin_number': 'VIN12345',
            'new_bike_odometer': 100,
            'new_bike_transmission': 'manual',
        }
        form = AdminUserBookingForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['service_type'], self.service_type)
        self.assertIsInstance(form.cleaned_data['appointment_datetime'], datetime.datetime)
        self.assertAlmostEqual(form.cleaned_data['appointment_datetime'], future_datetime, delta=datetime.timedelta(seconds=5))
        self.assertEqual(form.cleaned_data['booking_comments'], 'First service.')
        self.assertEqual(form.cleaned_data['user'], self.user)
        self.assertEqual(form.cleaned_data['bike_selection_type'], 'new')
        self.assertIsNone(form.cleaned_data['existing_motorcycle']) # Should be None when adding new
        self.assertEqual(form.cleaned_data['new_bike_make'], 'BMW')
        self.assertEqual(form.cleaned_data['new_bike_model'], 'S1000RR')
        self.assertEqual(form.cleaned_data['new_bike_year'], 2024)
        self.assertEqual(form.cleaned_data['new_bike_rego'], 'NEW1')
        self.assertEqual(form.cleaned_data['new_bike_vin_number'], 'VIN12345')
        self.assertEqual(form.cleaned_data['new_bike_odometer'], 100)
        self.assertEqual(form.cleaned_data['new_bike_transmission'], 'manual')

    # Test AdminUserBookingForm with missing user
    def test_admin_user_booking_form_missing_user(self):
        future_datetime = timezone.now() + datetime.timedelta(days=4)
        future_datetime = future_datetime.replace(second=0, microsecond=0)

        form_data = {
            'service_type': self.service_type.id,
            'appointment_datetime': future_datetime.strftime('%Y-%m-%dT%H:%M'),
            'bike_selection_type': 'existing',
            'existing_motorcycle': self.motorcycle1.id,
        }
        form = AdminUserBookingForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('user', form.errors)

    # Test AdminUserBookingForm with existing bike selected but no motorcycle provided
    def test_admin_user_booking_form_existing_bike_no_motorcycle(self):
        future_datetime = timezone.now() + datetime.timedelta(days=4)
        future_datetime = future_datetime.replace(second=0, microsecond=0)

        form_data = {
            'service_type': self.service_type.id,
            'appointment_datetime': future_datetime.strftime('%Y-%m-%dT%H:%M'),
            'user': self.user.id,
            'bike_selection_type': 'existing',
            'existing_motorcycle': '', # Missing existing motorcycle ID
        }
        form = AdminUserBookingForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('existing_motorcycle', form.errors)

    # Test AdminUserBookingForm with new bike selected but missing required new bike fields
    def test_admin_user_booking_form_new_bike_missing_fields(self):
        future_datetime = timezone.now() + datetime.timedelta(days=5)
        future_datetime = future_datetime.replace(second=0, microsecond=0)

        form_data = {
            'service_type': self.service_type.id,
            'appointment_datetime': future_datetime.strftime('%Y-%m-%dT%H:%M'),
            'user': self.user.id,
            'bike_selection_type': 'new',
            # Missing new_bike_make, new_bike_model, new_bike_year
            'new_bike_rego': 'NEW1',
        }
        form = AdminUserBookingForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('new_bike_make', form.errors)
        self.assertIn('new_bike_model', form.errors)
        self.assertIn('new_bike_year', form.errors)

    # Test AdminUserBookingForm with existing bike selected but new bike fields provided
    def test_admin_user_booking_form_existing_bike_with_new_fields(self):
        future_datetime = timezone.now() + datetime.timedelta(days=4)
        future_datetime = future_datetime.replace(second=0, microsecond=0)

        form_data = {
            'service_type': self.service_type.id,
            'appointment_datetime': future_datetime.strftime('%Y-%m-%dT%H:%M'),
            'user': self.user.id,
            'bike_selection_type': 'existing',
            'existing_motorcycle': self.motorcycle1.id,
            'new_bike_make': 'BMW', # Should not be here
        }
        form = AdminUserBookingForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors) # Check for non-field errors

    # Test AdminUserBookingForm with new bike selected but existing motorcycle provided
    def test_admin_user_booking_form_new_bike_with_existing_motorcycle(self):
        future_datetime = timezone.now() + datetime.timedelta(days=5)
        future_datetime = future_datetime.replace(second=0, microsecond=0)

        form_data = {
            'service_type': self.service_type.id,
            'appointment_datetime': future_datetime.strftime('%Y-%m-%dT%H:%M'),
            'user': self.user.id,
            'bike_selection_type': 'new',
            'existing_motorcycle': self.motorcycle1.id, # Should not be here
            'new_bike_make': 'BMW',
            'new_bike_model': 'S1000RR',
            'new_bike_year': 2024,
        }
        form = AdminUserBookingForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('existing_motorcycle', form.errors)

    # Test that the existing_motorcycle queryset is filtered based on the selected user
    def test_admin_user_booking_form_existing_motorcycle_queryset(self):
        form_data = {'user': self.user.id}
        form = AdminUserBookingForm(data=form_data)
        form.is_valid() # Trigger queryset filtering in clean or init if not already
        queryset = form.fields['existing_motorcycle'].queryset
        self.assertEqual(queryset.count(), 2)
        self.assertIn(self.motorcycle1, queryset)
        self.assertIn(self.motorcycle2, queryset)
        self.assertNotIn(self.other_user_motorcycle, queryset)

        # Test with a different user
        form_data = {'user': self.other_user.id}
        form = AdminUserBookingForm(data=form_data)
        form.is_valid()
        queryset = form.fields['existing_motorcycle'].queryset
        self.assertEqual(queryset.count(), 1)
        self.assertIn(self.other_user_motorcycle, queryset)
        self.assertNotIn(self.motorcycle1, queryset)

        # Test with no user selected
        form = AdminUserBookingForm()
        queryset = form.fields['existing_motorcycle'].queryset
        self.assertEqual(queryset.count(), 0)

    # Test that AdminUserBookingForm uses the correct widgets (removed preferred_contact from base form)
    def test_admin_user_booking_form_widget_types(self):
        form = AdminUserBookingForm()
        self.assertIsInstance(form.fields['service_type'].widget, forms.Select)
        self.assertIsInstance(form.fields['appointment_datetime'].widget, forms.DateTimeInput)
        self.assertIsInstance(form.fields['booking_comments'].widget, forms.Textarea)
        self.assertIsInstance(form.fields['user'].widget, forms.Select)
        self.assertIsInstance(form.fields['user_first_name'].widget, forms.TextInput)
        self.assertIsInstance(form.fields['user_last_name'].widget, forms.TextInput)
        self.assertIsInstance(form.fields['user_email'].widget, forms.EmailInput)
        self.assertIsInstance(form.fields['user_phone_number'].widget, forms.TextInput)
        self.assertIsInstance(form.fields['bike_selection_type'].widget, forms.RadioSelect)
        self.assertIsInstance(form.fields['existing_motorcycle'].widget, forms.Select)
        self.assertIsInstance(form.fields['new_bike_make'].widget, forms.TextInput)
        self.assertIsInstance(form.fields['new_bike_model'].widget, forms.TextInput)
        self.assertIsInstance(form.fields['new_bike_year'].widget, forms.NumberInput)
        self.assertIsInstance(form.fields['new_bike_rego'].widget, forms.TextInput)
        self.assertIsInstance(form.fields['new_bike_vin_number'].widget, forms.TextInput)
        self.assertIsInstance(form.fields['new_bike_odometer'].widget, forms.NumberInput)
        self.assertIsInstance(form.fields['new_bike_transmission'].widget, forms.Select)

    # Test updating user details fields are optional
    def test_admin_user_booking_form_update_user_optional(self):
        future_datetime = timezone.now() + datetime.timedelta(days=4)
        future_datetime = future_datetime.replace(second=0, microsecond=0)

        form_data = {
            'service_type': self.service_type.id,
            'appointment_datetime': future_datetime.strftime('%Y-%m-%dT%H:%M'),
            'booking_comments': 'Check brakes.',
            'user': self.user.id,
            'bike_selection_type': 'existing',
            'existing_motorcycle': self.motorcycle1.id,
            'user_first_name': '',
            'user_last_name': '',
            'user_email': '',
            'user_phone_number': '',
        }
        form = AdminUserBookingForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['user_first_name'], '')
        self.assertEqual(form.cleaned_data['user_last_name'], '')
        self.assertEqual(form.cleaned_data['user_email'], '')
        self.assertEqual(form.cleaned_data['user_phone_number'], '')