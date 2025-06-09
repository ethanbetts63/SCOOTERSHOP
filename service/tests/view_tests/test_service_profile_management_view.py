from django.test import TestCase, Client
from django.urls import reverse
from django.contrib import messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.http import HttpRequest
from django.utils import timezone # Import timezone for created_at ordering

# Import models and forms
from service.models import ServiceProfile
from service.forms import AdminServiceProfileForm

# Import factories for setting up test data
from ..test_helpers.model_factories import UserFactory, ServiceProfileFactory

class ServiceProfileManagementViewTest(TestCase):
    """
    Tests for the ServiceProfileManagementView.
    Covers access control, listing, search, and form submission (create via management view).
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods.
        Create various users and service profiles for testing different scenarios.
        """
        cls.staff_user = UserFactory(username='staff_user', is_staff=True, is_superuser=False)
        cls.superuser = UserFactory(username='superuser', is_staff=True, is_superuser=True)
        cls.regular_user = UserFactory(username='regular_user', is_staff=False, is_superuser=False)

        # Create multiple service profiles with varying data for search tests
        # Ensure distinct creation times for consistent ordering in tests
        cls.profile1 = ServiceProfileFactory(
            name="Alpha Profile", email="alpha@example.com", phone_number="1112223333",
            city="Springville", # Explicitly set city to ensure it contains 'ville'
            created_at=timezone.now() - timezone.timedelta(days=30),
            user=UserFactory(username='alpha_user')
        )
        cls.profile2 = ServiceProfileFactory(
            name="Beta Profile", email="beta@test.com", phone_number="4445556666",
            city="Shelbyville", # Explicitly set city to ensure it contains 'ville'
            created_at=timezone.now() - timezone.timedelta(days=20),
            user=UserFactory(username='beta_user')
        )
        cls.profile3 = ServiceProfileFactory(
            name="Gamma Profile", email="gamma@domain.net", phone_number="7778889999",
            address_line_1="123 Main St", country="US",
            created_at=timezone.now() - timezone.timedelta(days=10),
            user=None # No linked user for this one
        )
        cls.profile_new = ServiceProfileFactory(
            name="Newest Profile", email="newest@domain.com", phone_number="0001112222",
            city="New City", created_at=timezone.now(),
            user=UserFactory(username='newest_user')
        )

        # A user who is not linked to any service profile (for form submissions)
        cls.unlinked_user = UserFactory(username='unlinked_user_for_form', email='unlinked_form@example.com')


        # Define URLs for convenience from urls.py
        cls.list_url = reverse('service:admin_service_profiles')
        # The edit URL is handled by ServiceProfileCreateUpdateView, but we need its name here
        # for constructing the URL in tests that specifically open the edit form from the list page.
        cls.edit_url_name = 'service:admin_edit_service_profile' 
        cls.delete_url_name = 'service:admin_delete_service_profile'


    def setUp(self):
        """
        Set up for each test method.
        Initialize client and session.
        """
        self.client = Client()
        # Ensure session is saved to allow messages to persist
        self.session = self.client.session
        self.session.save()


    # --- Access Control Tests (UserPassesTestMixin, LoginRequiredMixin) ---

    def test_view_redirects_anonymous_user(self):
        """
        Ensure anonymous users are redirected to the login page for management view.
        """
        response = self.client.get(self.list_url)
        self.assertRedirects(response, reverse('users:login') + f'?next={self.list_url}')

    def test_view_denies_access_to_regular_user(self):
        """
        Ensure regular (non-staff/non-superuser) users are denied access to management view.
        """
        self.client.force_login(self.regular_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 403) # Forbidden

    def test_view_grants_access_to_staff_user(self):
        """
        Ensure staff users can access the management view.
        """
        self.client.force_login(self.staff_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)

    def test_view_grants_access_to_superuser(self):
        """
        Ensure superusers can access the management view.
        """
        self.client.force_login(self.superuser)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)


    # --- GET Request Tests (Listing & Search) ---

    def test_get_request_list_all_profiles(self):
        """
        Test GET request to list all service profiles without search term.
        """
        self.client.force_login(self.staff_user)
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'service/admin_service_profile_management.html')
        self.assertIn('profiles', response.context)
        self.assertIn('form', response.context)
        self.assertFalse(response.context['is_edit_mode'])
        self.assertIsNone(response.context['current_profile'])
        self.assertEqual(response.context['search_term'], '')

        # Check if all profiles are present and ordered correctly (by created_at descending)
        profiles_in_context = list(response.context['profiles'])
        expected_profiles = list(ServiceProfile.objects.all().order_by('-created_at'))
        self.assertListEqual(profiles_in_context, expected_profiles)
        self.assertEqual(len(profiles_in_context), ServiceProfile.objects.count())


    def test_get_request_search_by_name(self):
        """
        Test search functionality by profile name.
        """
        self.client.force_login(self.staff_user)
        search_term = "Alpha"
        response = self.client.get(f"{self.list_url}?q={search_term}")

        self.assertEqual(response.status_code, 200)
        self.assertIn('profiles', response.context)
        self.assertEqual(response.context['search_term'], search_term)

        profiles_in_context = list(response.context['profiles'])
        self.assertEqual(len(profiles_in_context), 1)
        self.assertEqual(profiles_in_context[0], self.profile1)


    def test_get_request_search_by_email(self):
        """
        Test search functionality by email.
        """
        self.client.force_login(self.staff_user)
        search_term = "beta@test.com"
        response = self.client.get(f"{self.list_url}?q={search_term}")
        profiles_in_context = list(response.context['profiles'])
        self.assertEqual(len(profiles_in_context), 1)
        self.assertEqual(profiles_in_context[0], self.profile2)

    def test_get_request_search_by_phone_number(self):
        """
        Test search functionality by phone number.
        """
        self.client.force_login(self.staff_user)
        search_term = "777888" # Partial match for profile3
        response = self.client.get(f"{self.list_url}?q={search_term}")
        profiles_in_context = list(response.context['profiles'])
        self.assertEqual(len(profiles_in_context), 1)
        self.assertEqual(profiles_in_context[0], self.profile3)

    def test_get_request_search_by_city(self):
        """
        Test search functionality by city.
        """
        self.client.force_login(self.staff_user)
        search_term = "ville" # Matches Springville and Shelbyville
        response = self.client.get(f"{self.list_url}?q={search_term}")
        profiles_in_context = list(response.context['profiles'])
        
        # Check that both matching profiles are present, regardless of exact order beyond the count
        self.assertEqual(len(profiles_in_context), 2)
        self.assertIn(self.profile1, profiles_in_context)
        self.assertIn(self.profile2, profiles_in_context)


    def test_get_request_search_by_linked_username(self):
        """
        Test search functionality by linked user's username.
        """
        self.client.force_login(self.staff_user)
        search_term = "alpha_user"
        response = self.client.get(f"{self.list_url}?q={search_term}")
        profiles_in_context = list(response.context['profiles'])
        self.assertEqual(len(profiles_in_context), 1)
        self.assertEqual(profiles_in_context[0], self.profile1)


    def test_get_request_no_search_results(self):
        """
        Test search functionality with a term that yields no results.
        """
        self.client.force_login(self.staff_user)
        search_term = "nonexistentprofile"
        response = self.client.get(f"{self.list_url}?q={search_term}")

        self.assertEqual(response.status_code, 200)
        self.assertIn('profiles', response.context)
        self.assertEqual(len(list(response.context['profiles'])), 0)
        self.assertEqual(response.context['search_term'], search_term)


    def test_get_request_edit_mode(self):
        """
        Test GET request to display the management view with a specific profile
        loaded into the form for editing.
        Note: The form displayed on the management page is the same AdminServiceProfileForm,
        but the POST for actual update happens via a separate URL (admin_edit_service_profile)
        handled by ServiceProfileCreateUpdateView. This test focuses on the GET display.
        """
        self.client.force_login(self.staff_user)
        # Construct the URL for editing, which should be the admin_edit_service_profile URL
        edit_url = reverse(self.edit_url_name, kwargs={'pk': self.profile1.pk})
        response = self.client.get(edit_url) # This GET request will hit the ServiceProfileCreateUpdateView

        self.assertEqual(response.status_code, 200)
        # The URL /admin/service-profiles/edit/<pk>/ renders admin_service_profile_form.html
        # as per your urls.py mapping to ServiceProfileCreateUpdateView.
        self.assertTemplateUsed(response, 'service/admin_service_profile_form.html')
        self.assertIn('form', response.context)
        self.assertTrue(response.context['is_edit_mode'])
        self.assertEqual(response.context['current_profile'], self.profile1)
        self.assertEqual(response.context['form'].instance, self.profile1)
        self.assertFalse(response.context['form'].is_bound) # Form is populated, but not bound by POST data


    def test_get_request_edit_mode_non_existent_profile(self):
        """
        Test GET request to edit a non-existent profile. Should return 404.
        """
        self.client.force_login(self.staff_user)
        non_existent_pk = self.profile1.pk + 9999
        # Construct the URL for editing a non-existent profile
        edit_url = reverse(self.edit_url_name, kwargs={'pk': non_existent_pk})
        response = self.client.get(edit_url)
        self.assertEqual(response.status_code, 404)


    # --- POST Request Tests (Create ONLY from Management View's Form) ---
    # The management view handles creation of new profiles if the form
    # on its page is submitted to its own URL (pk=None).

    def test_post_request_create_profile_valid(self):
        """
        Test valid POST request to create a new profile from the management view (list page).
        """
        self.client.force_login(self.staff_user)
        initial_count = ServiceProfile.objects.count()
        new_profile_data = {
            'user': self.unlinked_user.pk,
            'name': 'New Profile From Mgmt',
            'email': 'mgmt_create@example.com',
            'phone_number': '1234512345',
            'address_line_1': '1 Mgmt St',
            'city': 'Mgmtville',
            'state': 'MG',
            'post_code': '12345',
            'country': 'US',
        }
        # Post to the list URL (admin_service_profiles), which handles new creation
        response = self.client.post(self.list_url, new_profile_data, follow=True) # Follow redirect

        self.assertEqual(ServiceProfile.objects.count(), initial_count + 1)
        new_profile = ServiceProfile.objects.get(name='New Profile From Mgmt')
        self.assertRedirects(response, self.list_url)
        
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), f"Service Profile for '{new_profile.name}' created successfully.")
        self.assertEqual(messages_list[0].level, messages.SUCCESS)


    def test_post_request_create_profile_invalid(self):
        """
        Test invalid POST request to create a new profile from the management view (list page).
        """
        self.client.force_login(self.staff_user)
        initial_count = ServiceProfile.objects.count()
        invalid_data = {
            'user': '', # No user
            'name': '', # Missing name (required if no user)
            'email': 'invalid@example.com',
            'phone_number': '1234567890',
            'address_line_1': '1 Invalid St',
            'city': 'Invalidton',
            'state': 'IV',
            'post_code': '00000',
            'country': 'US',
        }
        # Post to the list URL (admin_service_profiles)
        response = self.client.post(self.list_url, invalid_data)

        self.assertEqual(ServiceProfile.objects.count(), initial_count) # No new profile
        self.assertEqual(response.status_code, 200) # Should re-render with errors
        self.assertTemplateUsed(response, 'service/admin_service_profile_management.html')
        self.assertIn('form', response.context)
        self.assertFalse(response.context['form'].is_valid())
        self.assertIn('name', response.context['form'].errors)

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), "Please correct the errors below.")
        self.assertEqual(messages_list[0].level, messages.ERROR)


class ServiceProfileDeleteViewTest(TestCase):
    """
    Tests for the ServiceProfileDeleteView.
    """

    @classmethod
    def setUpTestData(cls):
        cls.staff_user = UserFactory(username='staff_user', is_staff=True, is_superuser=False)
        cls.superuser = UserFactory(username='superuser', is_staff=True, is_superuser=True)
        cls.regular_user = UserFactory(username='regular_user', is_staff=False, is_superuser=False)
        cls.profile_to_delete = ServiceProfileFactory(name="Profile to Delete")
        cls.list_url = reverse('service:admin_service_profiles')
        cls.delete_url_name = 'service:admin_delete_service_profile'


    def setUp(self):
        self.client = Client()
        # Ensure session is saved to allow messages to persist
        self.session = self.client.session
        self.session.save()

    # --- Access Control Tests ---

    def test_view_redirects_anonymous_user(self):
        """
        Ensure anonymous users are redirected to login for delete view.
        """
        delete_url = reverse(self.delete_url_name, kwargs={'pk': self.profile_to_delete.pk})
        response = self.client.post(delete_url)
        self.assertRedirects(response, reverse('users:login') + f'?next={delete_url}')

    def test_view_denies_access_to_regular_user(self):
        """
        Ensure regular users are denied access to delete view.
        """
        self.client.force_login(self.regular_user)
        delete_url = reverse(self.delete_url_name, kwargs={'pk': self.profile_to_delete.pk})
        response = self.client.post(delete_url)
        self.assertEqual(response.status_code, 403)

    def test_view_grants_access_to_staff_user(self):
        """
        Ensure staff users can access delete view.
        (This test implicitly passes if the POST test below passes, as GET isn't typically used for delete).
        """
        self.client.force_login(self.staff_user)
        # A simple get would give 405 Method Not Allowed, but we test the POST below
        delete_url = reverse(self.delete_url_name, kwargs={'pk': self.profile_to_delete.pk})
        response = self.client.get(delete_url) # Test GET method explicitly, should be 405
        self.assertEqual(response.status_code, 405) # Method Not Allowed for GET


    # --- POST Request Tests (Deletion) ---

    def test_post_request_delete_profile_valid(self):
        """
        Test valid POST request to delete a ServiceProfile.
        """
        self.client.force_login(self.staff_user)
        profile_pk = self.profile_to_delete.pk
        profile_name = self.profile_to_delete.name
        initial_count = ServiceProfile.objects.count()

        delete_url = reverse(self.delete_url_name, kwargs={'pk': profile_pk})
        response = self.client.post(delete_url, follow=True) # Follow redirect

        self.assertEqual(ServiceProfile.objects.count(), initial_count - 1)
        self.assertFalse(ServiceProfile.objects.filter(pk=profile_pk).exists())
        self.assertRedirects(response, self.list_url)

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), f"Service Profile for '{profile_name}' deleted successfully.")
        self.assertEqual(messages_list[0].level, messages.SUCCESS)

    def test_post_request_delete_non_existent_profile(self):
        """
        Test POST request to delete a non-existent ServiceProfile. Should return 404.
        """
        self.client.force_login(self.staff_user)
        non_existent_pk = self.profile_to_delete.pk + 9999
        delete_url = reverse(self.delete_url_name, kwargs={'pk': non_existent_pk})
        response = self.client.post(delete_url)
        self.assertEqual(response.status_code, 404)

