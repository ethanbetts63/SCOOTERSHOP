from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.messages import get_messages
from django.contrib.messages.storage.fallback import FallbackStorage
import datetime
import uuid
from unittest.mock import patch, Mock, PropertyMock # Import PropertyMock

# Import the view to be tested
from service.views.v2_views.user_views.step2_motorcycle_selection_view import Step2MotorcycleSelectionView
from service.forms import MotorcycleSelectionForm, ADD_NEW_MOTORCYCLE_OPTION

# Import models and factories
from service.models import TempServiceBooking, ServiceProfile, CustomerMotorcycle, ServiceType
from ..test_helpers.model_factories import (
    UserFactory,
    ServiceProfileFactory,
    TempServiceBookingFactory,
    CustomerMotorcycleFactory,
    ServiceTypeFactory,
)


class Step2MotorcycleSelectionViewTest(TestCase):
    """
    Tests for the Step2MotorcycleSelectionView (dispatch, GET, and POST methods).
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up common data for all tests in this class.
        """
        cls.factory = RequestFactory()
        cls.user = UserFactory()
        cls.service_profile = ServiceProfileFactory(user=cls.user)
        cls.service_type = ServiceTypeFactory()
        cls.base_url = reverse('service:service_book_step2')

    def setUp(self):
        """
        Set up for each test method. Ensure a clean state and common request setup.
        """
        TempServiceBooking.objects.all().delete()
        CustomerMotorcycle.objects.all().delete()

        # Use self.client for tests that render templates or access context
        self.client.force_login(self.user) # Ensure user is logged in for most tests

        # Create a valid TempServiceBooking. Crucially, set customer_motorcycle to None
        # if the test expects it to be initially unset or to remain unset.
        # TempServiceBookingFactory's default creates one, so we override it here.
        self.temp_booking = TempServiceBookingFactory(
            service_type=self.service_type,
            service_profile=self.service_profile,
            service_date=datetime.date.today() + datetime.timedelta(days=7), # A valid date
            customer_motorcycle=None # Ensure it starts as None for tests that expect it
        )
        # Set the UUID in the client's session
        session = self.client.session
        session['temp_booking_uuid'] = str(self.temp_booking.session_uuid)
        session.save()

        # Ensure there's at least one motorcycle for the user by default, for tests that use it.
        # This one is *not* linked to temp_booking by default setUp.
        self.customer_motorcycle = CustomerMotorcycleFactory(service_profile=self.service_profile)

    # --- Dispatch Method Tests (using RequestFactory for specific pre-rendering checks) ---

    def test_dispatch_no_temp_booking_uuid_in_session(self):
        """
        Test dispatch redirects to core:index if 'temp_booking_uuid' is missing from session.
        Uses RequestFactory because we are testing the dispatch logic before template rendering.
        """
        request = self.factory.get(self.base_url)
        request.session = {} # No UUID in session
        request.user = self.user # Ensure user is logged in for this dispatch
        response = Step2MotorcycleSelectionView().dispatch(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('service:service'))

    def test_dispatch_invalid_temp_booking_uuid_in_session(self):
        """
        Test dispatch redirects to core:index if 'temp_booking_uuid' in session is invalid.
        """
        request = self.factory.get(self.base_url)
        request.session = {'temp_booking_uuid': str(uuid.uuid4())} # A valid UUID format, but not in DB
        request.user = self.user
        response = Step2MotorcycleSelectionView().dispatch(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('service:service'))
        self.assertNotIn('temp_booking_uuid', request.session)

    def test_dispatch_temp_booking_missing_service_profile(self):
        """
        Test dispatch redirects to core:index if temp_booking.service_profile is None.
        """
        self.temp_booking.service_profile = None
        self.temp_booking.save()
        request = self.factory.get(self.base_url)
        request.session = {'temp_booking_uuid': str(self.temp_booking.session_uuid)}
        request.user = self.user
        response = Step2MotorcycleSelectionView().dispatch(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('service:service_book_step3'))

    def test_dispatch_no_motorcycles_redirects_to_step3(self):
        """
        Test dispatch redirects to step3 if the user has no existing motorcycles.
        """
        CustomerMotorcycle.objects.all().delete()  # Ensure no motorcycles exist for the user
        request = self.factory.get(self.base_url)
        request.session = {'temp_booking_uuid': str(self.temp_booking.session_uuid)}
        request.user = self.user
        response = Step2MotorcycleSelectionView().dispatch(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('service:service_book_step3'))


    # --- GET Method Tests (using self.client) ---

    def test_get_renders_form_with_motorcycles(self):
        """
        Test GET request renders the form correctly with existing motorcycles.
        Uses self.client to get a response that includes context and template info.
        """
        # Ensure there is a motorcycle for this user before GETting the page
        CustomerMotorcycleFactory(service_profile=self.service_profile)
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'service/step2_motorcycle_selection.html')
        self.assertIsInstance(response.context['form'], MotorcycleSelectionForm)
        self.assertEqual(response.context['temp_booking'], self.temp_booking)
        # Check that the form's choices include the existing motorcycle
        form_choices = [choice[0] for choice in response.context['form'].fields['selected_motorcycle'].choices]
        self.assertIn(str(self.customer_motorcycle.pk), form_choices)
        self.assertIn(ADD_NEW_MOTORCYCLE_OPTION, form_choices)


    # --- POST Method Tests (using self.client) ---

    @patch('service.views.v2_views.user_views.step2_motorcycle_selection_view.MotorcycleSelectionForm')
    def test_post_select_new_motorcycle_redirects_to_step3(self, MockMotorcycleSelectionForm):
        """
        Test POST request redirects to Step 3 when 'Add New Motorcycle' is selected.
        """
        # Configure the mock form instance's behavior
        mock_form_instance = MockMotorcycleSelectionForm.return_value
        mock_form_instance.is_valid.return_value = True
        mock_form_instance.cleaned_data = {'selected_motorcycle': ADD_NEW_MOTORCYCLE_OPTION}

        response = self.client.post(self.base_url, {'selected_motorcycle': ADD_NEW_MOTORCYCLE_OPTION})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('service:service_book_step3'))
        # Ensure temp_booking's customer_motorcycle remains None (as set in setUp)
        self.temp_booking.refresh_from_db()
        self.assertIsNone(self.temp_booking.customer_motorcycle)
        # Verify the form was instantiated
        MockMotorcycleSelectionForm.assert_called_once()


    @patch('service.views.v2_views.user_views.step2_motorcycle_selection_view.MotorcycleSelectionForm')
    def test_post_select_existing_motorcycle_redirects_to_step4(self, MockMotorcycleSelectionForm):
        """
        Test POST request updates temp_booking with selected motorcycle and redirects to Step 4.
        """
        mock_form_instance = MockMotorcycleSelectionForm.return_value
        mock_form_instance.is_valid.return_value = True
        mock_form_instance.cleaned_data = {'selected_motorcycle': str(self.customer_motorcycle.pk)}

        response = self.client.post(self.base_url, {'selected_motorcycle': str(self.customer_motorcycle.pk)})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('service:service_book_step4'))

        # Verify temp_booking was updated with the correct motorcycle
        self.temp_booking.refresh_from_db()
        self.assertEqual(self.temp_booking.customer_motorcycle, self.customer_motorcycle)
        MockMotorcycleSelectionForm.assert_called_once()


    @patch('service.views.v2_views.user_views.step2_motorcycle_selection_view.MotorcycleSelectionForm')
    def test_post_invalid_motorcycle_selection_renders_form_with_error(self, MockMotorcycleSelectionForm):
        """
        Test POST with an invalid motorcycle ID (e.g., non-existent or not belonging to user).
        """
        mock_form_instance = MockMotorcycleSelectionForm.return_value
        mock_form_instance.is_valid.return_value = True # Form says it's valid, but get_object_or_404 will fail
        mock_form_instance.cleaned_data = {'selected_motorcycle': '9999'} # Non-existent ID
        # Crucially, set the errors property on the mock instance
        mock_form_instance.errors = {'selected_motorcycle': ["Invalid motorcycle selection."]}


        # Patch get_object_or_404 to raise DoesNotExist when called by the view
        with patch('service.views.v2_views.user_views.step2_motorcycle_selection_view.get_object_or_404', side_effect=CustomerMotorcycle.DoesNotExist):
            response = self.client.post(self.base_url, {'selected_motorcycle': '9999'})
            self.assertEqual(response.status_code, 200) # Should re-render the form
            self.assertTemplateUsed(response, 'service/step2_motorcycle_selection.html')
            self.assertIn('form', response.context)
            # Check for error in the form
            self.assertIn('selected_motorcycle', response.context['form'].errors)
            self.assertIn("Invalid motorcycle selection.", response.context['form'].errors['selected_motorcycle'])

            # Ensure temp_booking was NOT updated
            self.temp_booking.refresh_from_db()
            self.assertIsNone(self.temp_booking.customer_motorcycle)
        MockMotorcycleSelectionForm.assert_called_once()


    @patch('service.views.v2_views.user_views.step2_motorcycle_selection_view.MotorcycleSelectionForm')
    def test_post_form_not_valid_renders_form_with_errors(self, MockMotorcycleSelectionForm):
        """
        Test POST request with invalid form data (e.g., no selection).
        """
        mock_form_instance = MockMotorcycleSelectionForm.return_value
        mock_form_instance.is_valid.return_value = False
        # Set the errors property on the mock instance
        mock_form_instance.errors = {'selected_motorcycle': ['This field is required.']}

        response = self.client.post(self.base_url, {}) # Empty POST data, which will make form invalid
        self.assertEqual(response.status_code, 200) # Should re-render the form
        self.assertTemplateUsed(response, 'service/step2_motorcycle_selection.html')
        self.assertIn('form', response.context)
        # Check for error in the form
        self.assertIn('selected_motorcycle', response.context['form'].errors)
        self.assertIn("This field is required.", response.context['form'].errors['selected_motorcycle'])

        # Ensure temp_booking's customer_motorcycle remains None (as set in setUp)
        self.temp_booking.refresh_from_db()
        self.assertIsNone(self.temp_booking.customer_motorcycle)
        MockMotorcycleSelectionForm.assert_called_once()


    def test_post_authenticated_user_without_motorcycles_still_redirects_to_step3(self):
        """
        Test that if a user has no motorcycles, even on POST, they are redirected to Step 3.
        This tests the dispatch method's re-evaluation.
        """
        CustomerMotorcycle.objects.all().delete()  # Ensure no motorcycles exist for the user

        # The client will send the POST request, and dispatch will handle the redirection.
        response = self.client.post(self.base_url, {'selected_motorcycle': ADD_NEW_MOTORCYCLE_OPTION})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('service:service_book_step3'))
        self.temp_booking.refresh_from_db()
        self.assertIsNone(self.temp_booking.customer_motorcycle) # Still no motorcycle linked
