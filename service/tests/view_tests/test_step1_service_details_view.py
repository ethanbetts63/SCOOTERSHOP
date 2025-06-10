from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.messages import get_messages
# Import the storage class for messages
from django.contrib.messages.storage.fallback import FallbackStorage
import datetime
import uuid # Import uuid for generating valid UUIDs
from unittest.mock import patch, Mock

# Import the view to be tested
from service.views.user_views.step1_service_details_view import Step1ServiceDetailsView

# Import models and factories
from service.models import TempServiceBooking, ServiceSettings, BlockedServiceDate, CustomerMotorcycle
# Corrected import path for model factories
from ..test_helpers.model_factories import (
    ServiceSettingsFactory,
    ServiceTypeFactory,
    TempServiceBookingFactory,
    BlockedServiceDateFactory,
    UserFactory,
    ServiceProfileFactory,
    CustomerMotorcycleFactory,
)

class Step1ServiceDetailsViewTest(TestCase):
    """
    Tests for the Step1ServiceDetailsView (POST method).
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up common data for all tests in this class.
        """
        cls.factory = RequestFactory()
        # Create a mock user for authenticated requests
        cls.user = UserFactory()
        cls.service_profile = ServiceProfileFactory(user=cls.user)
        cls.service_type = ServiceTypeFactory() # A valid service type

        # Patch timezone.now() and timezone.localtime() for consistent date tests
        cls.fixed_now = datetime.datetime(2025, 6, 15, 10, 0, 0, tzinfo=datetime.timezone.utc)
        cls.fixed_local_date = datetime.date(2025, 6, 15) # Sunday, June 15, 2025

        cls.patcher_now = patch('django.utils.timezone.now', return_value=cls.fixed_now)
        cls.patcher_localtime = patch('django.utils.timezone.localtime', return_value=cls.fixed_now)

        cls.mock_now = cls.patcher_now.start()
        cls.mock_localtime = cls.patcher_localtime.start()

    @classmethod
    def tearDownClass(cls):
        """
        Clean up mocks after all tests are done.
        """
        cls.patcher_now.stop()
        cls.patcher_localtime.stop()
        super().tearDownClass()

    def setUp(self):
        """
        Set up for each test method. Ensure a clean state.
        """
        ServiceSettings.objects.all().delete()
        TempServiceBooking.objects.all().delete()
        BlockedServiceDate.objects.all().delete()
        CustomerMotorcycle.objects.all().delete() # Clear existing motorcycles

        # Create default service settings for most tests
        self.service_settings = ServiceSettingsFactory(
            enable_service_booking=True,
            allow_anonymous_bookings=True,
            booking_advance_notice=1, # 1 day notice
            booking_open_days="Mon,Tue,Wed,Thu,Fri,Sat,Sun" # All days open
        )
        
        # Initialize session for the request object
        # This is crucial as Django's RequestFactory doesn't automatically add a session.
        self.request = self.factory.post(reverse('core:index'), {}) # Use core:index as the base URL
        self.request.session = {} # Manually attach a session dictionary
        setattr(self.request, '_messages', FallbackStorage(self.request))
        setattr(self.request, '_get_messages', lambda: FallbackStorage(self.request))


        self.request.user = Mock(is_authenticated=False) # Default to anonymous user, can be overridden

    @patch('service.views.user_views.step1_service_details_view.ServiceDetailsForm')
    def test_invalid_form_submission(self, MockServiceDetailsForm):
        """
        Test that invalid form submission leads to error messages and redirection to index.
        """
        mock_form_instance = MockServiceDetailsForm.return_value
        mock_form_instance.is_valid.return_value = False
        mock_form_instance.errors = {'service_type': ['This field is required.']}

        # Use the pre-initialized self.request
        response = Step1ServiceDetailsView().post(self.request)

        self.assertEqual(response.status_code, 302) # Redirect
        self.assertEqual(response.url, reverse('core:index'))

        messages = list(get_messages(self.request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Error in service_type: This field is required.")
        MockServiceDetailsForm.assert_called_once_with(self.request.POST)
        self.assertEqual(TempServiceBooking.objects.count(), 0) # No booking created

    @patch('service.views.user_views.step1_service_details_view.ServiceDetailsForm')
    def test_service_booking_disabled(self, MockServiceDetailsForm):
        """
        Test that if service booking is disabled in settings, an error is shown.
        """
        self.service_settings.enable_service_booking = False
        self.service_settings.save()

        mock_form_instance = MockServiceDetailsForm.return_value
        mock_form_instance.is_valid.return_value = True
        mock_form_instance.cleaned_data = {
            'service_type': self.service_type,
            'service_date': self.fixed_local_date + datetime.timedelta(days=2) # Mon
        }

        # Use the pre-initialized self.request
        response = Step1ServiceDetailsView().post(self.request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('core:index'))

        messages = list(get_messages(self.request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Service bookings are currently disabled.")
        self.assertEqual(TempServiceBooking.objects.count(), 0)

    @patch('service.views.user_views.step1_service_details_view.ServiceDetailsForm')
    def test_anonymous_bookings_not_allowed(self, MockServiceDetailsForm):
        """
        Test that if anonymous bookings are not allowed, unauthenticated users get an error.
        """
        self.service_settings.allow_anonymous_bookings = False
        self.service_settings.save()

        mock_form_instance = MockServiceDetailsForm.return_value
        mock_form_instance.is_valid.return_value = True
        mock_form_instance.cleaned_data = {
            'service_type': self.service_type,
            'service_date': self.fixed_local_date + datetime.timedelta(days=2) # Mon
        }

        # Ensure user is unauthenticated (default, but explicit for clarity)
        self.request.user = Mock(is_authenticated=False)
        response = Step1ServiceDetailsView().post(self.request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('core:index'))

        messages = list(get_messages(self.request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Anonymous bookings are not allowed. Please log in to book a service.")
        self.assertEqual(TempServiceBooking.objects.count(), 0)

    @patch('service.views.user_views.step1_service_details_view.ServiceDetailsForm')
    def test_service_date_too_early(self, MockServiceDetailsForm):
        """
        Test that if the service date is earlier than booking_advance_notice, an error is shown.
        fixed_local_date is June 15 (Sunday). advance_notice is 1 day.
        Min allowed date is June 16 (Monday).
        """
        self.service_settings.booking_advance_notice = 1 # One day advance notice
        self.service_settings.save()

        mock_form_instance = MockServiceDetailsForm.return_value
        mock_form_instance.is_valid.return_value = True
        mock_form_instance.cleaned_data = {
            'service_type': self.service_type,
            'service_date': self.fixed_local_date # June 15 (Sunday), which is 0 days notice
        }

        self.request.user = Mock(is_authenticated=True) # Authenticated user
        response = Step1ServiceDetailsView().post(self.request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('core:index'))

        messages = list(get_messages(self.request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Service date must be at least 1 days from now. Please choose a later date.")
        self.assertEqual(TempServiceBooking.objects.count(), 0)

    @patch('service.views.user_views.step1_service_details_view.ServiceDetailsForm')
    def test_service_date_on_closed_day(self, MockServiceDetailsForm):
        """
        Test that if the service date falls on a non-open day, an error is shown.
        fixed_local_date is June 15 (Sunday). Set open days to Mon-Fri.
        """
        self.service_settings.booking_open_days = "Mon,Tue,Wed,Thu,Fri"
        self.service_settings.booking_advance_notice = 0 # Allow current day to be checked
        self.service_settings.save()

        mock_form_instance = MockServiceDetailsForm.return_value
        mock_form_instance.is_valid.return_value = True
        mock_form_instance.cleaned_data = {
            'service_type': self.service_type,
            'service_date': self.fixed_local_date # June 15 (Sunday)
        }

        self.request.user = Mock(is_authenticated=True)
        response = Step1ServiceDetailsView().post(self.request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('core:index'))

        messages = list(get_messages(self.request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Services are not available on Sundays.")
        self.assertEqual(TempServiceBooking.objects.count(), 0)

    @patch('service.views.user_views.step1_service_details_view.ServiceDetailsForm')
    def test_service_date_blocked(self, MockServiceDetailsForm):
        """
        Test that if the service date is within a blocked period, an error is shown.
        """
        blocked_date = self.fixed_local_date + datetime.timedelta(days=2) # Monday
        BlockedServiceDateFactory(start_date=blocked_date, end_date=blocked_date)

        mock_form_instance = MockServiceDetailsForm.return_value
        mock_form_instance.is_valid.return_value = True
        mock_form_instance.cleaned_data = {
            'service_type': self.service_type,
            'service_date': blocked_date
        }

        self.request.user = Mock(is_authenticated=True)
        response = Step1ServiceDetailsView().post(self.request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('core:index'))

        messages = list(get_messages(self.request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Selected service date overlaps with a blocked service period.")
        self.assertEqual(TempServiceBooking.objects.count(), 0)

    @patch('service.views.user_views.step1_service_details_view.ServiceDetailsForm')
    # Patch reverse for service_book_step2 and service_book_step3
    @patch('service.views.user_views.step1_service_details_view.reverse', side_effect=lambda *args, **kwargs: {
        'service:service_book_step2': '/service-book/step2/',
        'service:service_book_step3': '/service-book/step3/',
        'core:index': '/index/' # Ensure core:index is still handled
    }.get(args[0], reverse(*args, **kwargs))) # Fallback to original reverse for others
    def test_new_temp_booking_anonymous_no_motorcycles_redirect_step3(self, mock_reverse, MockServiceDetailsForm):
        """
        Test successful new TempServiceBooking creation for anonymous user,
        redirects to step 3.
        """
        mock_form_instance = MockServiceDetailsForm.return_value
        mock_form_instance.is_valid.return_value = True
        mock_form_instance.cleaned_data = {
            'service_type': self.service_type,
            'service_date': self.fixed_local_date + datetime.timedelta(days=2) # Monday (valid date)
        }

        # Use the pre-initialized self.request, ensuring a clean session
        self.request.session = {}
        self.request.user = Mock(is_authenticated=False) # Anonymous user

        response = Step1ServiceDetailsView().post(self.request)

        self.assertEqual(response.status_code, 302)
        # Should redirect to step 3 as anonymous and no motorcycles
        self.assertTrue(response.url.startswith('/service-book/step3/'))

        messages = list(get_messages(self.request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Service details selected. Please choose your motorcycle.")

        # Verify TempServiceBooking was created
        temp_booking = TempServiceBooking.objects.get()
        self.assertEqual(temp_booking.service_type, self.service_type)
        self.assertEqual(temp_booking.service_date, mock_form_instance.cleaned_data['service_date'])
        self.assertIsNone(temp_booking.service_profile) # Should be None for anonymous
        # Assert the correct session key
        self.assertIn('temp_service_booking_uuid', self.request.session)
        self.assertEqual(str(temp_booking.session_uuid), self.request.session['temp_service_booking_uuid'])


    @patch('service.views.user_views.step1_service_details_view.ServiceDetailsForm')
    # Patch reverse for service_book_step2 and service_book_step3
    @patch('service.views.user_views.step1_service_details_view.reverse', side_effect=lambda *args, **kwargs: {
        'service:service_book_step2': '/service-book/step2/',
        'service:service_book_step3': '/service-book/step3/',
        'core:index': '/index/'
    }.get(args[0], reverse(*args, **kwargs)))
    def test_new_temp_booking_authenticated_no_motorcycles_redirect_step3(self, mock_reverse, MockServiceDetailsForm):
        """
        Test successful new TempServiceBooking creation for authenticated user with no motorcycles,
        redirects to step 3.
        """
        mock_form_instance = MockServiceDetailsForm.return_value
        mock_form_instance.is_valid.return_value = True
        mock_form_instance.cleaned_data = {
            'service_type': self.service_type,
            'service_date': self.fixed_local_date + datetime.timedelta(days=2) # Monday (valid date)
        }

        # Use the pre-initialized self.request, ensuring a clean session
        self.request.session = {}
        self.request.user = self.user # Authenticated user (no motorcycles yet for this user)

        response = Step1ServiceDetailsView().post(self.request)

        self.assertEqual(response.status_code, 302)
        # Should redirect to step 3 as authenticated but no motorcycles
        self.assertTrue(response.url.startswith('/service-book/step3/'))

        messages = list(get_messages(self.request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Service details selected. Please choose your motorcycle.")

        # Verify TempServiceBooking was created
        temp_booking = TempServiceBooking.objects.get()
        self.assertEqual(temp_booking.service_type, self.service_type)
        self.assertEqual(temp_booking.service_date, mock_form_instance.cleaned_data['service_date'])
        self.assertEqual(temp_booking.service_profile, self.service_profile) # Should be linked
        # Assert the correct session key
        self.assertIn('temp_service_booking_uuid', self.request.session)
        self.assertEqual(str(temp_booking.session_uuid), self.request.session['temp_service_booking_uuid'])

    @patch('service.views.user_views.step1_service_details_view.ServiceDetailsForm')
    # Patch reverse for service_book_step2 and service_book_step3
    @patch('service.views.user_views.step1_service_details_view.reverse', side_effect=lambda *args, **kwargs: {
        'service:service_book_step2': '/service-book/step2/',
        'service:service_book_step3': '/service-book/step3/',
        'core:index': '/index/'
    }.get(args[0], reverse(*args, **kwargs)))
    def test_new_temp_booking_authenticated_with_motorcycles_redirect_step2(self, mock_reverse, MockServiceDetailsForm):
        """
        Test successful new TempServiceBooking creation for authenticated user with motorcycles,
        redirects to step 2.
        """
        CustomerMotorcycleFactory(service_profile=self.service_profile) # Create a motorcycle for the user

        mock_form_instance = MockServiceDetailsForm.return_value
        mock_form_instance.is_valid.return_value = True
        mock_form_instance.cleaned_data = {
            'service_type': self.service_type,
            'service_date': self.fixed_local_date + datetime.timedelta(days=2) # Monday (valid date)
        }

        # Use the pre-initialized self.request, ensuring a clean session
        self.request.session = {}
        self.request.user = self.user # Authenticated user with motorcycles

        response = Step1ServiceDetailsView().post(self.request)

        self.assertEqual(response.status_code, 302)
        # Should redirect to step 2 as authenticated and has motorcycles
        self.assertTrue(response.url.startswith('/service-book/step2/'))

        messages = list(get_messages(self.request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Service details selected. Please choose your motorcycle.")

        # Verify TempServiceBooking was created
        temp_booking = TempServiceBooking.objects.get()
        self.assertEqual(temp_booking.service_type, self.service_type)
        self.assertEqual(temp_booking.service_date, mock_form_instance.cleaned_data['service_date'])
        self.assertEqual(temp_booking.service_profile, self.service_profile)
        # Assert the correct session key
        self.assertIn('temp_service_booking_uuid', self.request.session)
        self.assertEqual(str(temp_booking.session_uuid), self.request.session['temp_service_booking_uuid'])

    @patch('service.views.user_views.step1_service_details_view.ServiceDetailsForm')
    # Patch reverse for service_book_step2 and service_book_step3
    @patch('service.views.user_views.step1_service_details_view.reverse', side_effect=lambda *args, **kwargs: {
        'service:service_book_step2': '/service-book/step2/',
        'service:service_book_step3': '/service-book/step3/',
        'core:index': '/index/'
    }.get(args[0], reverse(*args, **kwargs)))
    def test_update_existing_temp_booking(self, mock_reverse, MockServiceDetailsForm):
        """
        Test that an existing TempServiceBooking is updated if session_uuid is present.
        """
        existing_temp_booking = TempServiceBookingFactory(
            service_type=ServiceTypeFactory(), # Different service type initially
            service_date=self.fixed_local_date + datetime.timedelta(days=5), # Different date initially
            service_profile=self.service_profile # Link to the user's profile
        )

        mock_form_instance = MockServiceDetailsForm.return_value
        mock_form_instance.is_valid.return_value = True
        mock_form_instance.cleaned_data = {
            'service_type': self.service_type, # New service type
            'service_date': self.fixed_local_date + datetime.timedelta(days=2) # New date
        }

        # Use the pre-initialized self.request and set its session
        # Use the correct session key
        self.request.session = {'temp_service_booking_uuid': str(existing_temp_booking.session_uuid)}
        self.request.user = self.user # Authenticated user with motorcycles (to ensure redirect path)
        CustomerMotorcycleFactory(service_profile=self.service_profile) # Ensure motorcycles exist

        response = Step1ServiceDetailsView().post(self.request)

        self.assertEqual(response.status_code, 302)
        # Should redirect to step 2 as authenticated and has motorcycles
        self.assertTrue(response.url.startswith('/service-book/step2/'))

        messages = list(get_messages(self.request))
        self.assertEqual(len(messages), 1)
        # Correct the expected message
        self.assertEqual(str(messages[0]), "Service details updated. Please choose your motorcycle.")

        # Verify the existing TempServiceBooking was updated, not a new one created
        self.assertEqual(TempServiceBooking.objects.count(), 1)
        updated_temp_booking = TempServiceBooking.objects.get(session_uuid=existing_temp_booking.session_uuid)
        self.assertEqual(updated_temp_booking.service_type, self.service_type) # Should be updated
        self.assertEqual(updated_temp_booking.service_date, mock_form_instance.cleaned_data['service_date']) # Should be updated
        self.assertEqual(updated_temp_booking.service_profile, self.service_profile) # Should remain linked

    @patch('service.views.user_views.step1_service_details_view.ServiceDetailsForm')
    def test_exception_during_save(self, MockServiceDetailsForm):
        """
        Test handling of unexpected exceptions during TempServiceBooking save.
        """
        mock_form_instance = MockServiceDetailsForm.return_value
        mock_form_instance.is_valid.return_value = True
        mock_form_instance.cleaned_data = {
            'service_type': self.service_type,
            'service_date': self.fixed_local_date + datetime.timedelta(days=2) # Monday
        }

        # Patch TempServiceBooking.objects.create to raise an exception
        with patch('service.views.user_views.step1_service_details_view.TempServiceBooking.objects.create',
                   side_effect=Exception("Database error!")):
            
            # Use the pre-initialized self.request
            self.request.session = {} # Ensure clean session for this test
            self.request.user = Mock(is_authenticated=False) # Anonymous user

            response = Step1ServiceDetailsView().post(self.request)

            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, reverse('core:index'))

            messages = list(get_messages(self.request))
            self.assertEqual(len(messages), 1)
            self.assertTrue("An unexpected error occurred while saving your selection" in str(messages[0]))
            self.assertEqual(TempServiceBooking.objects.count(), 0) # No booking created

    @patch('service.views.user_views.step1_service_details_view.ServiceDetailsForm')
    def test_session_reference_cleared(self, MockServiceDetailsForm):
        """
        Test that 'service_booking_reference' is cleared from session on POST.
        """
        mock_form_instance = MockServiceDetailsForm.return_value
        mock_form_instance.is_valid.return_value = True
        mock_form_instance.cleaned_data = {
            'service_type': self.service_type,
            'service_date': self.fixed_local_date + datetime.timedelta(days=2) # Monday
        }

        # Create a real TempServiceBooking with a valid UUID for this test
        # This ensures the .get() call in the view does not fail due to a badly formed UUID
        existing_temp_booking_for_test = TempServiceBookingFactory(
            service_type=self.service_type,
            service_date=self.fixed_local_date + datetime.timedelta(days=1),
            service_profile=self.service_profile # Associate with a profile if authenticated user
        )

        # Use the pre-initialized self.request and set its session and user
        # Use the correct session key
        self.request.session = {
            'service_booking_reference': 'OLDREF123',
            'temp_service_booking_uuid': str(existing_temp_booking_for_test.session_uuid) # Use a valid UUID
        }
        self.request.user = self.user # Use the authenticated user
        CustomerMotorcycleFactory(service_profile=self.service_profile) # Ensure motorcycles exist for this user

        response = Step1ServiceDetailsView().post(self.request)

        self.assertNotIn('service_booking_reference', self.request.session)
        # The 'temp_service_booking_uuid' should remain in the session or be updated.
        self.assertIn('temp_service_booking_uuid', self.request.session)
        self.assertEqual(str(existing_temp_booking_for_test.session_uuid), self.request.session['temp_service_booking_uuid'])

