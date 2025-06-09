from django.test import TestCase, Client
from django.urls import reverse
from django.contrib import messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.http import HttpRequest # Import HttpRequest

# Import models and factories for setting up test data
from service.models import ServiceProfile
from service.forms import AdminServiceProfileForm # Make sure this import path is correct
from ..test_helpers.model_factories import UserFactory, ServiceProfileFactory

class ServiceProfileCreateUpdateViewTest(TestCase):
    """
    Tests for the ServiceProfileCreateUpdateView.
    Covers access control, GET requests (create/update), and POST requests (create/update, valid/invalid).
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods.
        Create different types of users and service profiles for testing access and view logic.
        """
        cls.staff_user = UserFactory(username='staff_user', is_staff=True, is_superuser=False)
        cls.superuser = UserFactory(username='superuser', is_staff=True, is_superuser=True)
        cls.regular_user = UserFactory(username='regular_user', is_staff=False, is_superuser=False)

        cls.existing_profile = ServiceProfileFactory(name="Existing Profile for Test", email="existing@example.com")
        cls.existing_profile_user = cls.existing_profile.user # If it's linked to a user

        # Define URLs for convenience
        cls.create_url = reverse('service:admin_create_service_profile') # Assuming this is your URL name for creation
        cls.update_url = reverse('service:admin_edit_service_profile', kwargs={'pk': cls.existing_profile.pk})


    def setUp(self):
        """
        Set up for each test method.
        Initialize client and message storage for each test to avoid interference.
        """
        self.client = Client()
        # Set up Django messages storage for testing messages
        # Note: For messages to work correctly with self.client.post/get,
        # messages should ideally be retrieved from the response object or its internal request.
        # The below setup is for ensuring the messages framework is available,
        # but actual retrieval often uses response.wsgi_request.
        self.session = self.client.session
        self.session.save()
        # You don't need to manually create an HttpRequest object for client tests
        # as the client handles it internally. Messages are typically
        # accessed via response.wsgi_request once the response is received.


    # --- Access Control Tests (UserPassesTestMixin, LoginRequiredMixin) ---

    def test_view_redirects_anonymous_user(self):
        """
        Ensure anonymous users are redirected to the login page.
        """
        response = self.client.get(self.create_url)
        self.assertRedirects(response, reverse('users:login') + f'?next={self.create_url}') # Assuming 'users:login' is your login URL name

        response = self.client.get(self.update_url)
        self.assertRedirects(response, reverse('users:login') + f'?next={self.update_url}')

    def test_view_denies_access_to_regular_user(self):
        """
        Ensure regular (non-staff/non-superuser) users are denied access.
        """
        self.client.force_login(self.regular_user)
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 403) # Forbidden

        response = self.client.get(self.update_url)
        self.assertEqual(response.status_code, 403) # Forbidden

    def test_view_grants_access_to_staff_user(self):
        """
        Ensure staff users can access the view.
        """
        self.client.force_login(self.staff_user)
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 200)

        response = self.client.get(self.update_url)
        self.assertEqual(response.status_code, 200)

    def test_view_grants_access_to_superuser(self):
        """
        Ensure superusers can access the view.
        """
        self.client.force_login(self.superuser)
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 200)

        response = self.client.get(self.update_url)
        self.assertEqual(response.status_code, 200)


    # --- GET Request Tests ---

    def test_get_request_create_new_profile(self):
        """
        Test GET request for displaying the form to create a new ServiceProfile.
        """
        self.client.force_login(self.staff_user)
        response = self.client.get(self.create_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'service/admin_service_profile_form.html')
        self.assertIsInstance(response.context['form'], AdminServiceProfileForm)
        self.assertFalse(response.context['is_edit_mode'])
        self.assertIsNone(response.context['current_profile'])
        # Check that the form is unbound (no initial data from an instance)
        self.assertFalse(response.context['form'].is_bound)

    def test_get_request_update_existing_profile(self):
        """
        Test GET request for displaying the form to update an existing ServiceProfile.
        """
        self.client.force_login(self.staff_user)
        response = self.client.get(self.update_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'service/admin_service_profile_form.html')
        self.assertIsInstance(response.context['form'], AdminServiceProfileForm)
        self.assertTrue(response.context['is_edit_mode'])
        self.assertEqual(response.context['current_profile'], self.existing_profile)
        # Fix for is_bound: A form initialized with an instance is not 'bound'
        # in the sense of having POST data, but rather populated.
        # We check the instance directly.
        self.assertEqual(response.context['form'].instance, self.existing_profile)
        # Ensure the form's 'is_bound' status reflects no POST data
        self.assertFalse(response.context['form'].is_bound)


    def test_get_request_update_non_existent_profile(self):
        """
        Test GET request for an update URL with a non-existent PK.
        Should return 404.
        """
        self.client.force_login(self.staff_user)
        non_existent_pk = self.existing_profile.pk + 9999
        non_existent_url = reverse('service:admin_edit_service_profile', kwargs={'pk': non_existent_pk})
        response = self.client.get(non_existent_url)
        self.assertEqual(response.status_code, 404)


    # --- POST Request Tests (Create) ---

    def test_post_request_create_new_profile_valid(self):
        """
        Test POST request for creating a new ServiceProfile with valid data.
        """
        self.client.force_login(self.staff_user)
        initial_profile_count = ServiceProfile.objects.count()
        new_user = UserFactory(username='new_linked_user', email='new_linked@example.com')

        data = {
            'user': new_user.pk,
            'name': 'New Valid Profile',
            'email': 'newvalid@example.com',
            'phone_number': '1234567890',
            'address_line_1': '100 New St',
            'city': 'Newville',
            'state': 'NV',
            'post_code': '99999',
            'country': 'US',
        }
        response = self.client.post(self.create_url, data)

        self.assertEqual(ServiceProfile.objects.count(), initial_profile_count + 1)
        new_profile = ServiceProfile.objects.get(name='New Valid Profile')
        self.assertEqual(new_profile.user, new_user)
        self.assertRedirects(response, reverse('service:admin_service_profiles')) # Redirect to list view
        
        # Fix for messages: Get messages from the response's request
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), f"Service Profile for '{new_profile.name}' created successfully.")
        self.assertEqual(messages_list[0].level, messages.SUCCESS)

    def test_post_request_create_new_profile_invalid(self):
        """
        Test POST request for creating a new ServiceProfile with invalid data.
        (e.g., missing required fields when no user is linked).
        """
        self.client.force_login(self.staff_user)
        initial_profile_count = ServiceProfile.objects.count()

        data = {
            'user': '', # No user linked
            'name': '', # Missing required name
            'email': 'invalid@example.com',
            'phone_number': '1234567890',
            'address_line_1': '100 New St',
            'city': 'Newville',
            'state': 'NV',
            'post_code': '99999',
            'country': 'US',
        }
        response = self.client.post(self.create_url, data)

        self.assertEqual(ServiceProfile.objects.count(), initial_profile_count) # No new profile created
        self.assertEqual(response.status_code, 200) # Should render the form again with errors
        self.assertTemplateUsed(response, 'service/admin_service_profile_form.html')
        self.assertIn('form', response.context)
        self.assertFalse(response.context['form'].is_valid())
        self.assertIn('name', response.context['form'].errors) # Verify specific error
        
        # Fix for messages: Get messages from the response's request
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), "Please correct the errors below.")
        self.assertEqual(messages_list[0].level, messages.ERROR)


    # --- POST Request Tests (Update) ---

    def test_post_request_update_existing_profile_valid(self):
        """
        Test POST request for updating an existing ServiceProfile with valid data.
        """
        self.client.force_login(self.staff_user)
        original_name = self.existing_profile.name
        updated_name = "Updated Existing Profile Name"

        data = {
            'user': self.existing_profile_user.pk if self.existing_profile_user else '', # Keep the same user or no user
            'name': updated_name, # Change the name
            'email': 'updated_existing@example.com',
            'phone_number': self.existing_profile.phone_number,
            'address_line_1': self.existing_profile.address_line_1,
            'city': self.existing_profile.city,
            'state': self.existing_profile.state,
            'post_code': self.existing_profile.post_code,
            'country': self.existing_profile.country,
        }
        response = self.client.post(self.update_url, data)

        self.existing_profile.refresh_from_db() # Reload the instance from the database
        self.assertEqual(self.existing_profile.name, updated_name)
        self.assertRedirects(response, reverse('service:admin_service_profiles'))
        
        # Fix for messages: Get messages from the response's request
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), f"Service Profile for '{self.existing_profile.name}' updated successfully.")
        self.assertEqual(messages_list[0].level, messages.SUCCESS)


    def test_post_request_update_existing_profile_invalid(self):
        """
        Test POST request for updating an existing ServiceProfile with invalid data.
        (e.g., attempting to link to an already linked user, or missing required fields).
        """
        self.client.force_login(self.staff_user)
        original_name = self.existing_profile.name

        # Scenario: Try to link the existing profile to a user already linked to *another* profile
        another_linked_user = ServiceProfileFactory().user # Creates another user with a linked profile

        data = {
            'user': another_linked_user.pk, # Invalid: user already linked elsewhere
            'name': original_name,
            'email': self.existing_profile.email,
            'phone_number': self.existing_profile.phone_number,
            'address_line_1': self.existing_profile.address_line_1,
            'city': self.existing_profile.city,
            'state': self.existing_profile.state,
            'post_code': self.existing_profile.post_code,
            'country': self.existing_profile.country,
        }
        response = self.client.post(self.update_url, data)

        self.assertEqual(response.status_code, 200) # Should render the form again with errors
        self.assertTemplateUsed(response, 'service/admin_service_profile_form.html')
        self.assertIn('form', response.context)
        self.assertFalse(response.context['form'].is_valid())
        self.assertIn('user', response.context['form'].errors) # Verify specific error
        self.assertIn(f"This user ({another_linked_user.username}) is already linked to another Service Profile.", response.context['form'].errors['user'])
        
        # Fix for messages: Get messages from the response's request
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), "Please correct the errors below.")
        self.assertEqual(messages_list[0].level, messages.ERROR)

        # Verify the profile was NOT updated
        self.existing_profile.refresh_from_db()
        self.assertEqual(self.existing_profile.name, original_name) # Name should not have changed


    def test_post_request_update_non_existent_profile(self):
        """
        Test POST request for an update URL with a non-existent PK.
        Should return 404.
        """
        self.client.force_login(self.staff_user)
        non_existent_pk = self.existing_profile.pk + 9999
        non_existent_url = reverse('service:admin_edit_service_profile', kwargs={'pk': non_existent_pk})

        data = { # Valid data, but target doesn't exist
            'name': 'Should not matter',
            'email': 'shouldnotmatter@example.com',
            'phone_number': '1231231234',
            'address_line_1': '100 New St',
            'city': 'Newville',
            'state': 'NV',
            'post_code': '99999',
            'country': 'US',
        }
        response = self.client.post(non_existent_url, data)
        self.assertEqual(response.status_code, 404)

