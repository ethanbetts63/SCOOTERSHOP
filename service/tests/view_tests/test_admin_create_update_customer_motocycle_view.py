from django.test import TestCase, Client
from django.urls import reverse
from django.contrib import messages
from service.models import CustomerMotorcycle
from service.forms import AdminCustomerMotorcycleForm

# Import factories for setting up test data
from ..test_helpers.model_factories import UserFactory, CustomerMotorcycleFactory, ServiceProfileFactory

# Removed os and shutil imports as temporary MEDIA_ROOT is not needed

class CustomerMotorcycleCreateUpdateViewTest(TestCase):
    """
    Tests for the CustomerMotorcycleCreateUpdateView.
    Covers access control, GET requests (create/update), and POST requests (create/update, valid/invalid).
    Image upload testing has been explicitly removed as requested.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods.
        Create different types of users and related objects for testing.
        """
        cls.staff_user = UserFactory(username='staff_motorcycle_user', is_staff=True, is_superuser=False)
        cls.superuser = UserFactory(username='superuser_motorcycle', is_staff=True, is_superuser=True)
        cls.regular_user = UserFactory(username='regular_motorcycle_user', is_staff=False, is_superuser=False)

        cls.service_profile = ServiceProfileFactory(name="Motorcycle Owner Profile")
        cls.existing_motorcycle = CustomerMotorcycleFactory(
            brand="ExistingBrand", model="ExistingModel", rego="EX123",
            service_profile=cls.service_profile
        )

        # Define URLs for convenience
        cls.create_url = reverse('service:admin_create_customer_motorcycle')
        cls.update_url = reverse('service:admin_edit_customer_motorcycle', kwargs={'pk': cls.existing_motorcycle.pk})
        cls.list_management_url = reverse('service:admin_customer_motorcycle_management') # Assuming this URL exists for redirect

    def setUp(self):
        """
        Set up for each test method.
        Initialize client.
        """
        self.client = Client()
        self.session = self.client.session
        self.session.save()
        
        # Removed temporary media root setup as image tests are removed


    # Removed tearDown method as temporary media root cleanup is not needed


    # --- Access Control Tests ---

    def test_view_redirects_anonymous_user(self):
        """
        Ensure anonymous users are redirected to the login page.
        """
        response = self.client.get(self.create_url)
        self.assertRedirects(response, reverse('users:login') + f'?next={self.create_url}')

        response = self.client.get(self.update_url)
        self.assertRedirects(response, reverse('users:login') + f'?next={self.update_url}')

    def test_view_denies_access_to_regular_user(self):
        """
        Ensure regular users are denied access.
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

    def test_get_request_create_new_motorcycle(self):
        """
        Test GET request for displaying the form to create a new CustomerMotorcycle.
        """
        self.client.force_login(self.staff_user)
        response = self.client.get(self.create_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'service/admin_customer_motorcycle_create_update.html')
        self.assertIsInstance(response.context['form'], AdminCustomerMotorcycleForm)
        self.assertFalse(response.context['is_edit_mode'])
        self.assertIsNone(response.context['current_motorcycle'])
        self.assertFalse(response.context['form'].is_bound)

    def test_get_request_update_existing_motorcycle(self):
        """
        Test GET request for displaying the form to update an existing CustomerMotorcycle.
        """
        self.client.force_login(self.staff_user)
        response = self.client.get(self.update_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'service/admin_customer_motorcycle_create_update.html')
        self.assertIsInstance(response.context['form'], AdminCustomerMotorcycleForm)
        self.assertTrue(response.context['is_edit_mode'])
        self.assertEqual(response.context['current_motorcycle'], self.existing_motorcycle)
        self.assertEqual(response.context['form'].instance, self.existing_motorcycle)
        self.assertFalse(response.context['form'].is_bound)


    def test_get_request_update_non_existent_motorcycle(self):
        """
        Test GET request for an update URL with a non-existent PK.
        Should return 404.
        """
        self.client.force_login(self.staff_user)
        non_existent_pk = self.existing_motorcycle.pk + 9999
        non_existent_url = reverse('service:admin_edit_customer_motorcycle', kwargs={'pk': non_existent_pk})
        response = self.client.get(non_existent_url)
        self.assertEqual(response.status_code, 404)


    # --- POST Request Tests (Create) ---

    def test_post_request_create_new_motorcycle_valid(self):
        """
        Test POST request for creating a new CustomerMotorcycle with valid data.
        """
        self.client.force_login(self.staff_user)
        initial_count = CustomerMotorcycle.objects.count()

        data = {
            'service_profile': self.service_profile.pk,
            'brand': 'NewBrand',
            'model': 'NewModel',
            'year': 2020,
            'rego': 'NEW123',
            'odometer': 1000,
            'transmission': 'MANUAL',
            'engine_size': '500cc',
            'vin_number': 'ABCDEF12345678901', # 17 chars
            'engine_number': 'NEWENG123',
        }
        # Removed files=files as image tests are removed
        response = self.client.post(self.create_url, data, follow=True)

        self.assertEqual(CustomerMotorcycle.objects.count(), initial_count + 1)
        new_motorcycle = CustomerMotorcycle.objects.get(brand='NewBrand')
        self.assertEqual(new_motorcycle.model, 'NewModel')
        # Removed image assertion
        self.assertRedirects(response, self.list_management_url) # Redirect to list view
        
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), f"Motorcycle '{new_motorcycle}' created successfully.")
        self.assertEqual(messages_list[0].level, messages.SUCCESS)

    def test_post_request_create_new_motorcycle_invalid(self):
        """
        Test POST request for creating a new CustomerMotorcycle with invalid data.
        (e.g., missing required fields).
        """
        self.client.force_login(self.staff_user)
        initial_count = CustomerMotorcycle.objects.count()

        invalid_data = {
            'service_profile': self.service_profile.pk,
            'brand': '', # Missing required field
            'model': 'InvalidModel',
            'year': 2020,
            'rego': 'INVLD',
            'odometer': 100,
            'transmission': 'MANUAL',
            'engine_size': '100cc',
        }
        response = self.client.post(self.create_url, invalid_data)

        self.assertEqual(CustomerMotorcycle.objects.count(), initial_count) # No new motorcycle created
        self.assertEqual(response.status_code, 200) # Should render the form again with errors
        self.assertTemplateUsed(response, 'service/admin_customer_motorcycle_create_update.html')
        self.assertIn('form', response.context)
        self.assertFalse(response.context['form'].is_valid())
        self.assertIn('brand', response.context['form'].errors) # Verify specific error

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), "Please correct the errors below.")
        self.assertEqual(messages_list[0].level, messages.ERROR)

    # --- POST Request Tests (Update) ---

    def test_post_request_update_existing_motorcycle_valid(self):
        """
        Test POST request for updating an existing CustomerMotorcycle with valid data.
        """
        self.client.force_login(self.staff_user)
        original_brand = self.existing_motorcycle.brand
        updated_brand = "UpdatedBrand"

        data = {
            'service_profile': self.existing_motorcycle.service_profile.pk,
            'brand': updated_brand, # Change the brand
            'model': self.existing_motorcycle.model,
            'year': self.existing_motorcycle.year,
            'rego': self.existing_motorcycle.rego,
            'odometer': self.existing_motorcycle.odometer,
            'transmission': self.existing_motorcycle.transmission,
            'engine_size': self.existing_motorcycle.engine_size,
            'vin_number': self.existing_motorcycle.vin_number,
            'engine_number': self.existing_motorcycle.engine_number,
        }
        response = self.client.post(self.update_url, data, follow=True)

        self.existing_motorcycle.refresh_from_db() # Reload the instance from the database
        self.assertEqual(self.existing_motorcycle.brand, updated_brand)
        self.assertRedirects(response, self.list_management_url)
        
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), f"Motorcycle '{self.existing_motorcycle}' updated successfully.")
        self.assertEqual(messages_list[0].level, messages.SUCCESS)

    # Removed test_post_request_update_existing_motorcycle_with_new_image

    def test_post_request_update_existing_motorcycle_invalid(self):
        """
        Test POST request for updating an existing CustomerMotorcycle with invalid data.
        (e.g., missing required fields).
        """
        self.client.force_login(self.staff_user)
        original_model = self.existing_motorcycle.model

        invalid_data = {
            'service_profile': self.existing_motorcycle.service_profile.pk,
            'brand': self.existing_motorcycle.brand,
            'model': '', # Invalid: Missing required field
            'year': self.existing_motorcycle.year,
            'rego': self.existing_motorcycle.rego,
            'odometer': self.existing_motorcycle.odometer,
            'transmission': self.existing_motorcycle.transmission,
            'engine_size': self.existing_motorcycle.engine_size,
        }
        response = self.client.post(self.update_url, invalid_data)

        self.assertEqual(response.status_code, 200) # Should render the form again with errors
        self.assertTemplateUsed(response, 'service/admin_customer_motorcycle_create_update.html')
        self.assertIn('form', response.context)
        self.assertFalse(response.context['form'].is_valid())
        self.assertIn('model', response.context['form'].errors) # Verify specific error

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), "Please correct the errors below.")
        self.assertEqual(messages_list[0].level, messages.ERROR)

        self.existing_motorcycle.refresh_from_db()
        self.assertEqual(self.existing_motorcycle.model, original_model) # Ensure no change occurred


    def test_post_request_update_non_existent_motorcycle(self):
        """
        Test POST request for an update URL with a non-existent PK.
        Should return 404.
        """
        self.client.force_login(self.staff_user)
        non_existent_pk = self.existing_motorcycle.pk + 9999
        non_existent_url = reverse('service:admin_edit_customer_motorcycle', kwargs={'pk': non_existent_pk})

        data = { # Valid data, but target doesn't exist
            'brand': 'NonExistent',
            'model': 'NonExistent',
            'year': 2020,
            'rego': 'NOPE',
            'odometer': 100,
            'transmission': 'MANUAL',
            'engine_size': '100cc',
            'service_profile': self.service_profile.pk,
        }
        response = self.client.post(non_existent_url, data)
        self.assertEqual(response.status_code, 404)

