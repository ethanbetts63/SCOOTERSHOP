# service/tests/test_step4_service_profile_view.py

from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.messages import get_messages
from django.contrib.auth import get_user_model
import datetime
import uuid

# Import the view to be tested
# Assuming your view is in service.views.user_views.step4_service_profile_view
# Adjust the import path if necessary.
from service.views.v2_views.user_views import Step4ServiceProfileView
from service.forms.step4_service_profile_form import ServiceBookingUserForm

# Import models and factories
from service.models import TempServiceBooking, ServiceProfile, CustomerMotorcycle, ServiceType, ServiceSettings
# Adjust the import path for model_factories if it's different
from ..test_helpers.model_factories import (
    UserFactory,
    ServiceProfileFactory,
    TempServiceBookingFactory,
    CustomerMotorcycleFactory,
    ServiceTypeFactory,
    ServiceSettingsFactory,
)

User = get_user_model()

class Step4ServiceProfileViewTest(TestCase):
    """
    Tests for the Step4ServiceProfileView (dispatch, GET, and POST methods).
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up common data for all tests in this class.
        """
        cls.factory = RequestFactory()
        cls.user_password = 'testpassword123'
        cls.user = UserFactory(password=cls.user_password) # For authenticated tests
        cls.other_user = UserFactory(username="otheruser", email="other@example.com", password=cls.user_password)

        cls.service_type = ServiceTypeFactory()
        cls.service_settings = ServiceSettingsFactory() # Ensure settings exist
        cls.base_url = reverse('service:service_book_step4')

    def setUp(self):
        """
        Set up for each test method.
        """
        # Clear relevant models before each test
        TempServiceBooking.objects.all().delete()
        ServiceProfile.objects.all().delete()
        CustomerMotorcycle.objects.all().delete()

        # Motorcycle is required to reach Step 4
        # This motorcycle will be linked to the temp_booking
        self.motorcycle_for_temp_booking = CustomerMotorcycleFactory(
            brand="Honda", model="CBR", year=2020, rego="STEP4MC"
        )
        # ^ service_profile for this motorcycle will be set during POST tests of Step 4

        self.temp_booking = TempServiceBookingFactory(
            service_type=self.service_type,
            service_date=datetime.date.today() + datetime.timedelta(days=10),
            customer_motorcycle=self.motorcycle_for_temp_booking, # Link motorcycle from step 3
            service_profile=None # Starts as None, will be set/created in Step 4
        )

        # Set the UUID in the client's session
        session = self.client.session
        session['temp_booking_uuid'] = str(self.temp_booking.session_uuid)
        session.save()
        
        # Default valid data for POST requests (can be overridden in specific tests)
        self.valid_post_data = {
            'name': 'Test User Name',
            'email': 'testuser@example.com',
            'phone_number': '0123456789',
            'address_line_1': '123 Test St',
            'address_line_2': '',
            'city': 'Testville',
            'state': 'TS',
            'post_code': '12345',
            'country': 'Testland',
        }

    # --- Dispatch Method Tests ---

    def test_dispatch_no_temp_booking_uuid_in_session_redirects(self):
        self.client.logout() # Ensure clean session
        session = self.client.session
        if 'temp_booking_uuid' in session:
            del session['temp_booking_uuid']
        session.save()

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 302)
        # Assuming redirection to step1 if session is completely lost
        self.assertRedirects(response, reverse('service:service'))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Your booking session has expired or is invalid." in str(m) for m in messages))


    def test_dispatch_invalid_temp_booking_uuid_redirects(self):
        session = self.client.session
        session['temp_booking_uuid'] = str(uuid.uuid4()) # Non-existent UUID
        session.save()

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('service:service'))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Your booking session could not be found." in str(m) for m in messages))


    def test_dispatch_no_motorcycle_on_temp_booking_redirects_to_step3(self):
        self.temp_booking.customer_motorcycle = None
        self.temp_booking.save()
        # Re-set session as temp_booking was modified
        session = self.client.session
        session['temp_booking_uuid'] = str(self.temp_booking.session_uuid)
        session.save()

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('service:service_book_step3'))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Please select or add your motorcycle details first (Step 3)." in str(m) for m in messages))

    def test_dispatch_valid_temp_booking_proceeds(self):
        # self.client.force_login(self.user) # Login user
        # Session already set up in self.setUp()
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200) # Should render the form
        self.assertTemplateUsed(response, 'service/step4_service_profile.html')

    # --- GET Method Tests ---

    def test_get_anonymous_user_renders_blank_form(self):
        self.client.logout() # Ensure anonymous
        # Re-set session after logout
        session = self.client.session
        session['temp_booking_uuid'] = str(self.temp_booking.session_uuid)
        session.save()

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context['form'], ServiceBookingUserForm)
        self.assertIsNone(response.context['form'].instance.pk) # New instance

    def test_get_auth_user_no_profile_renders_blank_form(self):
        self.client.force_login(self.user)
        # Ensure user has no existing ServiceProfile
        ServiceProfile.objects.filter(user=self.user).delete()

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context['form'], ServiceBookingUserForm)
        self.assertIsNone(response.context['form'].instance.pk) # New instance

    def test_get_auth_user_with_profile_renders_prefilled_form(self):
        self.client.force_login(self.user)
        user_profile = ServiceProfileFactory(user=self.user, name="Existing User Profile")

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertIsInstance(form, ServiceBookingUserForm)
        self.assertEqual(form.instance, user_profile)
        self.assertEqual(form.initial['name'], "Existing User Profile")

    def test_get_temp_booking_has_profile_precedence_over_user_profile(self):
        self.client.force_login(self.user)
        user_profile = ServiceProfileFactory(user=self.user, name="User's Own Profile")
        # A different profile is already on temp_booking (e.g., user went back and changed mind)
        temp_booking_profile = ServiceProfileFactory(name="Profile From TempBooking")
        self.temp_booking.service_profile = temp_booking_profile
        self.temp_booking.save()

        # Re-set session as temp_booking was modified
        session = self.client.session
        session['temp_booking_uuid'] = str(self.temp_booking.session_uuid)
        session.save()

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertIsInstance(form, ServiceBookingUserForm)
        self.assertEqual(form.instance, temp_booking_profile) # Should use profile from temp_booking
        self.assertEqual(form.initial['name'], "Profile From TempBooking")


    # --- POST Method Tests ---

    def test_post_anonymous_user_create_profile_valid_data(self):
        self.client.logout()
        session = self.client.session
        session['temp_booking_uuid'] = str(self.temp_booking.session_uuid)
        session.save()

        initial_profile_count = ServiceProfile.objects.count()
        response = self.client.post(self.base_url, self.valid_post_data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('service:service_book_step5'))
        self.assertEqual(ServiceProfile.objects.count(), initial_profile_count + 1)

        new_profile = ServiceProfile.objects.get(email=self.valid_post_data['email'])
        self.assertIsNone(new_profile.user) # Anonymous, so no user linked

        self.temp_booking.refresh_from_db()
        self.assertEqual(self.temp_booking.service_profile, new_profile)

        self.motorcycle_for_temp_booking.refresh_from_db()
        self.assertEqual(self.motorcycle_for_temp_booking.service_profile, new_profile)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Your details have been saved successfully." in str(m) for m in messages))

    def test_post_auth_user_no_profile_create_profile_valid_data(self):
        self.client.force_login(self.user)
        ServiceProfile.objects.filter(user=self.user).delete() # Ensure no profile

        initial_profile_count = ServiceProfile.objects.count()
        response = self.client.post(self.base_url, self.valid_post_data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('service:service_book_step5'))
        self.assertEqual(ServiceProfile.objects.count(), initial_profile_count + 1)

        new_profile = ServiceProfile.objects.get(email=self.valid_post_data['email'])
        self.assertEqual(new_profile.user, self.user) # User should be linked

        self.temp_booking.refresh_from_db()
        self.assertEqual(self.temp_booking.service_profile, new_profile)

        self.motorcycle_for_temp_booking.refresh_from_db()
        self.assertEqual(self.motorcycle_for_temp_booking.service_profile, new_profile)

    def test_post_auth_user_with_profile_update_profile_valid_data(self):
        self.client.force_login(self.user)
        existing_profile = ServiceProfileFactory(user=self.user, name="Old Name", email="old_email@example.com")
        self.temp_booking.service_profile = existing_profile # Simulate it was loaded in GET
        self.temp_booking.save()
        
        session = self.client.session # Re-save session
        session['temp_booking_uuid'] = str(self.temp_booking.session_uuid)
        session.save()

        updated_data = self.valid_post_data.copy()
        updated_data['name'] = "Updated Name"
        updated_data['email'] = existing_profile.email # Keep same email to update existing

        initial_profile_count = ServiceProfile.objects.count()
        response = self.client.post(self.base_url, updated_data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('service:service_book_step5'))
        self.assertEqual(ServiceProfile.objects.count(), initial_profile_count) # No new profile

        existing_profile.refresh_from_db()
        self.assertEqual(existing_profile.name, "Updated Name")
        self.assertEqual(existing_profile.user, self.user)

        self.temp_booking.refresh_from_db()
        self.assertEqual(self.temp_booking.service_profile, existing_profile)

        self.motorcycle_for_temp_booking.refresh_from_db()
        self.assertEqual(self.motorcycle_for_temp_booking.service_profile, existing_profile)

    def test_post_invalid_data_rerenders_form_with_errors(self):
        self.client.force_login(self.user)
        invalid_data = self.valid_post_data.copy()
        invalid_data['email'] = "notanemail" # Invalid email

        initial_profile_count = ServiceProfile.objects.count()
        motorcycle_initial_profile = self.motorcycle_for_temp_booking.service_profile

        response = self.client.post(self.base_url, invalid_data)

        self.assertEqual(response.status_code, 200) # Re-render
        self.assertTemplateUsed(response, 'service/step4_service_profile.html')
        self.assertIn('form', response.context)
        form = response.context['form']
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors) # Check for email error

        self.assertEqual(ServiceProfile.objects.count(), initial_profile_count) # No new profile
        
        self.temp_booking.refresh_from_db() # Profile on temp_booking should not be set yet
        self.assertIsNone(self.temp_booking.service_profile)

        self.motorcycle_for_temp_booking.refresh_from_db() # Motorcycle's profile should not be changed
        self.assertEqual(self.motorcycle_for_temp_booking.service_profile, motorcycle_initial_profile)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Please correct the errors below." in str(m) for m in messages))

    def test_post_updates_motorcycle_profile_if_not_already_set(self):
        self.client.force_login(self.user)
        # Ensure motorcycle has no profile initially for this specific test
        self.motorcycle_for_temp_booking.service_profile = None
        self.motorcycle_for_temp_booking.save()

        response = self.client.post(self.base_url, self.valid_post_data)
        self.assertEqual(response.status_code, 302)

        new_profile = ServiceProfile.objects.get(email=self.valid_post_data['email'])
        self.motorcycle_for_temp_booking.refresh_from_db()
        self.assertEqual(self.motorcycle_for_temp_booking.service_profile, new_profile)

    def test_post_updates_motorcycle_profile_if_different(self):
        self.client.force_login(self.user)
        old_motorcycle_profile = ServiceProfileFactory(name="Old Bike Owner Profile")
        self.motorcycle_for_temp_booking.service_profile = old_motorcycle_profile
        self.motorcycle_for_temp_booking.save()

        # Temp booking will get a new/updated profile from the form
        response = self.client.post(self.base_url, self.valid_post_data)
        self.assertEqual(response.status_code, 302)

        # The new profile created/updated by the form submission
        form_submitted_profile = ServiceProfile.objects.get(email=self.valid_post_data['email'])
        
        self.motorcycle_for_temp_booking.refresh_from_db()
        # Motorcycle's profile should now be the one from the form, not the `old_motorcycle_profile`
        self.assertEqual(self.motorcycle_for_temp_booking.service_profile, form_submitted_profile)
        self.assertNotEqual(self.motorcycle_for_temp_booking.service_profile, old_motorcycle_profile)

