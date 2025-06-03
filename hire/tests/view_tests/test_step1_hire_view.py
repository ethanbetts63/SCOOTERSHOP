import datetime
import uuid
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.messages import get_messages

# Import models
from hire.models import TempHireBooking, DriverProfile
from dashboard.models import HireSettings, BlockedHireDate
from django.contrib.auth import get_user_model

# Import model factories
from hire.tests.test_helpers.model_factories import (
    create_hire_settings,
    create_user,
    create_driver_profile,
)

User = get_user_model()


class SelectDateTimeViewTests(TestCase):
    """
    Tests for the SelectDateTimeView (Step 1 of the booking process).
    """

    def setUp(self):
        """
        Set up common test data and client.
        """
        self.client = Client()
        # Ensure HireSettings exists for all tests
        self.hire_settings = create_hire_settings(
            minimum_hire_duration_hours=2,
            maximum_hire_duration_days=30,
            booking_lead_time_hours=2,
            pick_up_start_time=datetime.time(9, 0),
            pick_up_end_time=datetime.time(17, 0),
            return_off_start_time=datetime.time(9, 0),
            return_end_time=datetime.time(17, 0),
            default_daily_rate=Decimal('90.00'), # Ensure this is set for other factories that might use it
        )
        # Corrected URL name based on hire/urls.py
        self.url = reverse('hire:step1_select_datetime')
        self.redirect_url_step2 = reverse('hire:step2_choose_bike')

        # Define a valid future date and time for testing
        self.valid_pickup_datetime = timezone.now() + datetime.timedelta(days=5, hours=3)
        self.valid_return_datetime = self.valid_pickup_datetime + datetime.timedelta(days=2)

        self.valid_form_data = {
            'pick_up_date': self.valid_pickup_datetime.strftime('%Y-%m-%d'),
            'pick_up_time': self.valid_pickup_datetime.strftime('%H:%M'),
            'return_date': self.valid_return_datetime.strftime('%Y-%m-%d'),
            'return_time': self.valid_return_datetime.strftime('%H:%M'),
            'has_motorcycle_license': 'on', # Checkbox value
        }

    def _get_messages(self, response):
        """Helper to extract messages from response."""
        return [m.message for m in get_messages(response.wsgi_request)]

    # --- Test Successful Form Submissions ---

    def test_post_valid_data_new_temp_booking_anonymous_user(self):
        """
        Test valid form submission creates a new TempHireBooking for an anonymous user.
        """
        self.assertEqual(TempHireBooking.objects.count(), 0)

        response = self.client.post(self.url, self.valid_form_data, follow=True)

        self.assertEqual(response.status_code, 200) # Should redirect successfully
        self.assertEqual(TempHireBooking.objects.count(), 1) # A new booking should be created

        temp_booking = TempHireBooking.objects.first()
        self.assertIsNotNone(temp_booking)
        self.assertEqual(temp_booking.pickup_date, self.valid_pickup_datetime.date())
        self.assertEqual(temp_booking.pickup_time, self.valid_pickup_datetime.time().replace(second=0, microsecond=0)) # Compare times without seconds/microseconds
        self.assertEqual(temp_booking.return_date, self.valid_return_datetime.date())
        self.assertEqual(temp_booking.return_time, self.valid_return_datetime.time().replace(second=0, microsecond=0))
        self.assertTrue(temp_booking.has_motorcycle_license)
        self.assertIsNone(temp_booking.driver_profile) # Anonymous user, no driver profile linked yet

        # Check redirection URL with query parameters
        expected_redirect_path = f"{self.redirect_url_step2}?temp_booking_id={temp_booking.id}&temp_booking_uuid={temp_booking.session_uuid}"
        self.assertRedirects(response, expected_redirect_path)

        # Check success message
        messages = self._get_messages(response)
        self.assertIn("Dates selected. Please choose your motorcycle.", messages)

    def test_post_valid_data_new_temp_booking_authenticated_user_no_driver_profile(self):
        """
        Test valid form submission creates a new TempHireBooking for an authenticated user
        who doesn't have a DriverProfile yet.
        """
        user = create_user(username="testuser")
        self.client.force_login(user)
        self.assertEqual(TempHireBooking.objects.count(), 0)
        self.assertFalse(hasattr(user, 'driver_profile')) # Ensure no driver profile exists

        response = self.client.post(self.url, self.valid_form_data, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(TempHireBooking.objects.count(), 1)

        temp_booking = TempHireBooking.objects.first()
        self.assertIsNotNone(temp_booking)
        self.assertIsNone(temp_booking.driver_profile) # Still no driver profile linked at this stage

        expected_redirect_path = f"{self.redirect_url_step2}?temp_booking_id={temp_booking.id}&temp_booking_uuid={temp_booking.session_uuid}"
        self.assertRedirects(response, expected_redirect_path)
        messages = self._get_messages(response)
        self.assertIn("Dates selected. Please choose your motorcycle.", messages)

    def test_post_valid_data_new_temp_booking_authenticated_user_with_driver_profile(self):
        """
        Test valid form submission creates a new TempHireBooking for an authenticated user
        who already has a DriverProfile.
        """
        user = create_user(username="testuser")
        driver_profile = create_driver_profile(user=user) # Create driver profile for the user
        self.client.force_login(user)
        self.assertEqual(TempHireBooking.objects.count(), 0)
        self.assertTrue(hasattr(user, 'driver_profile')) # Ensure driver profile exists

        response = self.client.post(self.url, self.valid_form_data, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(TempHireBooking.objects.count(), 1)

        temp_booking = TempHireBooking.objects.first()
        self.assertIsNotNone(temp_booking)
        # Driver profile should be linked immediately if it exists for authenticated user
        self.assertEqual(temp_booking.driver_profile, driver_profile)

        expected_redirect_path = f"{self.redirect_url_step2}?temp_booking_id={temp_booking.id}&temp_booking_uuid={temp_booking.session_uuid}"
        self.assertRedirects(response, expected_redirect_path)
        messages = self._get_messages(response)
        self.assertIn("Dates selected. Please choose your motorcycle.", messages)

    def test_post_valid_data_update_existing_temp_booking(self):
        """
        Test valid form submission updates an existing TempHireBooking.
        """
        # Create an initial TempHireBooking and store its ID in session
        initial_pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        initial_return_date = initial_pickup_date + datetime.timedelta(days=1)
        initial_temp_booking = TempHireBooking.objects.create(
            session_uuid=uuid.uuid4(),
            pickup_date=initial_pickup_date,
            pickup_time=datetime.time(9, 0),
            return_date=initial_return_date,
            return_time=datetime.time(17, 0),
            has_motorcycle_license=False,
        )
        session = self.client.session
        session['temp_booking_id'] = initial_temp_booking.id
        session['temp_booking_uuid'] = str(initial_temp_booking.session_uuid)
        session.save()

        self.assertEqual(TempHireBooking.objects.count(), 1)

        # Submit new valid data
        response = self.client.post(self.url, self.valid_form_data, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(TempHireBooking.objects.count(), 1) # No new booking created

        updated_temp_booking = TempHireBooking.objects.get(id=initial_temp_booking.id)
        self.assertEqual(updated_temp_booking.pickup_date, self.valid_pickup_datetime.date())
        self.assertEqual(updated_temp_booking.pickup_time, self.valid_pickup_datetime.time().replace(second=0, microsecond=0))
        self.assertEqual(updated_temp_booking.return_date, self.valid_return_datetime.date())
        self.assertEqual(updated_temp_booking.return_time, self.valid_return_datetime.time().replace(second=0, microsecond=0))
        self.assertTrue(updated_temp_booking.has_motorcycle_license)

        expected_redirect_path = f"{self.redirect_url_step2}?temp_booking_id={updated_temp_booking.id}&temp_booking_uuid={updated_temp_booking.session_uuid}"
        self.assertRedirects(response, expected_redirect_path)
        messages = self._get_messages(response)
        # Corrected assertion for the updated message
        self.assertIn("Dates updated. Please choose your motorcycle.", messages)

    # --- Test Invalid Form Submissions (Form-level errors) ---

    def test_post_invalid_data_return_before_pickup_date(self):
        """
        Test invalid form submission where return date is before pickup date.
        """
        invalid_data = self.valid_form_data.copy()
        invalid_data['return_date'] = (self.valid_pickup_datetime - datetime.timedelta(days=1)).strftime('%Y-%m-%d')

        response = self.client.post(self.url, invalid_data, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, self.redirect_url_step2) # Should redirect back to step2
        self.assertEqual(TempHireBooking.objects.count(), 0) # No booking created/updated

        messages = self._get_messages(response)
        self.assertIn("Return date and time must be after pickup date and time.", messages)

    def test_post_invalid_data_missing_required_field(self):
        """
        Test invalid form submission with a missing required field.
        """
        invalid_data = self.valid_form_data.copy()
        del invalid_data['pick_up_date'] # Remove a required field

        response = self.client.post(self.url, invalid_data, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, self.redirect_url_step2)
        self.assertEqual(TempHireBooking.objects.count(), 0)

        messages = self._get_messages(response)
        self.assertIn("This field is required.", messages) # Generic error for missing field

    # --- Test View-level Validations (HireSettings and BlockedHireDate) ---

    def test_post_data_violates_minimum_hire_duration(self):
        """
        Test form submission where hire duration is less than minimum_hire_duration_hours.
        """
        # Set hire settings for this specific test
        self.hire_settings.minimum_hire_duration_hours = 24 # 24 hours minimum
        self.hire_settings.save()

        # Create data with duration less than 24 hours (e.g., 1 hour)
        pickup_dt = timezone.now() + datetime.timedelta(days=5, hours=3)
        return_dt = pickup_dt + datetime.timedelta(hours=1) # 1 hour duration

        invalid_data = {
            'pick_up_date': pickup_dt.strftime('%Y-%m-%d'),
            'pick_up_time': pickup_dt.strftime('%H:%M'),
            'return_date': return_dt.strftime('%Y-%m-%d'),
            'return_time': return_dt.strftime('%H:%M'),
            'has_motorcycle_license': 'on',
        }

        response = self.client.post(self.url, invalid_data, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, self.redirect_url_step2)
        self.assertEqual(TempHireBooking.objects.count(), 0)

        messages = self._get_messages(response)
        self.assertIn(f"Hire duration must be at least {self.hire_settings.minimum_hire_duration_hours} hours.", messages)

    def test_post_data_violates_maximum_hire_duration(self):
        """
        Test form submission where hire duration is greater than maximum_hire_duration_days.
        """
        # Set hire settings for this specific test
        self.hire_settings.maximum_hire_duration_days = 3 # 3 days maximum
        self.hire_settings.save()

        # Create data with duration greater than 3 days (e.g., 4 days)
        pickup_dt = timezone.now() + datetime.timedelta(days=5, hours=3)
        return_dt = pickup_dt + datetime.timedelta(days=4) # 4 days duration

        invalid_data = {
            'pick_up_date': pickup_dt.strftime('%Y-%m-%d'),
            'pick_up_time': pickup_dt.strftime('%H:%M'),
            'return_date': return_dt.strftime('%Y-%m-%d'),
            'return_time': return_dt.strftime('%H:%M'),
            'has_motorcycle_license': 'on',
        }

        response = self.client.post(self.url, invalid_data, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, self.redirect_url_step2)
        self.assertEqual(TempHireBooking.objects.count(), 0)

        messages = self._get_messages(response)
        self.assertIn(f"Hire duration cannot exceed {self.hire_settings.maximum_hire_duration_days} days.", messages)

    def test_post_data_violates_booking_lead_time(self):
        """
        Test form submission where pickup time is less than booking_lead_time_hours from now.
        """
        # Set hire settings for this specific test
        self.hire_settings.booking_lead_time_hours = 24 # 24 hours lead time
        self.hire_settings.save()

        # Create data with pickup time less than 24 hours from now (e.g., 1 hour from now)
        pickup_dt = timezone.now() + datetime.timedelta(hours=1)
        return_dt = pickup_dt + datetime.timedelta(days=1) # Ensure valid duration

        invalid_data = {
            'pick_up_date': pickup_dt.strftime('%Y-%m-%d'),
            'pick_up_time': pickup_dt.strftime('%H:%M'),
            'return_date': return_dt.strftime('%Y-%m-%d'),
            'return_time': return_dt.strftime('%H:%M'),
            'has_motorcycle_license': 'on',
        }

        response = self.client.post(self.url, invalid_data, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, self.redirect_url_step2)
        self.assertEqual(TempHireBooking.objects.count(), 0)

        messages = self._get_messages(response)
        self.assertIn(f"Pickup must be at least {self.hire_settings.booking_lead_time_hours} hours from now.", messages)

    def test_post_data_overlaps_blocked_hire_date(self):
        """
        Test form submission where selected dates overlap with a BlockedHireDate.
        """
        # Create a blocked date range
        blocked_start = self.valid_pickup_datetime.date() + datetime.timedelta(days=1)
        blocked_end = self.valid_pickup_datetime.date() + datetime.timedelta(days=3)
        # Corrected keyword argument from 'reason' to 'description'
        BlockedHireDate.objects.create(start_date=blocked_start, end_date=blocked_end, description="Maintenance")

        # Create form data that overlaps the blocked period
        # Example: Pickup 0 days after blocked_start, Return 2 days after blocked_start
        pickup_dt = blocked_start
        return_dt = blocked_start + datetime.timedelta(days=2)

        invalid_data = {
            'pick_up_date': pickup_dt.strftime('%Y-%m-%d'),
            'pick_up_time': datetime.time(10, 0).strftime('%H:%M'),
            'return_date': return_dt.strftime('%Y-%m-%d'),
            'return_time': datetime.time(16, 0).strftime('%H:%M'),
            'has_motorcycle_license': 'on',
        }

        response = self.client.post(self.url, invalid_data, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, self.redirect_url_step2)
        self.assertEqual(TempHireBooking.objects.count(), 0)

        messages = self._get_messages(response)
        self.assertIn("Selected dates overlap with a blocked hire period.", messages)

    def test_post_data_no_motorcycle_license(self):
        """
        Test valid form submission when has_motorcycle_license is false.
        """
        valid_data_no_license = self.valid_form_data.copy()
        valid_data_no_license['has_motorcycle_license'] = '' # Unchecked checkbox

        response = self.client.post(self.url, valid_data_no_license, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(TempHireBooking.objects.count(), 1)
        temp_booking = TempHireBooking.objects.first()
        self.assertFalse(temp_booking.has_motorcycle_license)

        expected_redirect_path = f"{self.redirect_url_step2}?temp_booking_id={temp_booking.id}&temp_booking_uuid={temp_booking.session_uuid}"
        self.assertRedirects(response, expected_redirect_path)
        messages = self._get_messages(response)
        self.assertIn("Dates selected. Please choose your motorcycle.", messages)

