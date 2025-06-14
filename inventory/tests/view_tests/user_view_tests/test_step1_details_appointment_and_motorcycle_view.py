# inventory/tests/test_views/test_step1_sales_profile_view.py

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest import mock
import os
import tempfile
from PIL import Image # Required for creating dummy image files

from inventory.models import TempSalesBooking, SalesProfile, InventorySettings
from ...test_helpers.model_factories import (
    TempSalesBookingFactory,
    InventorySettingsFactory,
    UserFactory,
    SalesProfileFactory,
    MotorcycleFactory
)

class Step1SalesProfileViewTest(TestCase):
    """
    Tests for the Step1SalesProfileView.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up common data for all tests in this class.
        """
        cls.client = Client()
        cls.url = reverse('inventory:step1_sales_profile')

        # Ensure a singleton InventorySettings instance exists
        cls.inventory_settings = InventorySettingsFactory(
            require_drivers_license=False, # Default to False for most tests
            require_address_info=False,    # Default to False for most tests
        )

        # Create a dummy motorcycle for TempSalesBookingFactory
        cls.motorcycle = MotorcycleFactory()

        # Create a user for authenticated tests
        cls.user = UserFactory(username='testuser', email='test@example.com')
        cls.user.set_password('password123')
        cls.user.save()


    def _create_temp_booking_in_session(self, client, user=None, sales_profile=None):
        """Helper to create a TempSalesBooking and set its ID in the session."""
        temp_booking = TempSalesBookingFactory(
            motorcycle=self.motorcycle,
            sales_profile=sales_profile,
            booking_status='pending_details' # Initial status for Step 1
        )
        session = client.session
        session['current_temp_booking_id'] = temp_booking.pk
        session.save()
        return temp_booking

    def _create_dummy_image(self, name='test_image.jpg', size=(50, 50), color=(255, 0, 0)):
        """Helper to create a dummy image file for upload."""
        file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
        img = Image.new('RGB', size, color)
        img.save(file, 'jpeg')
        file.close()
        return SimpleUploadedFile(name, open(file.name, 'rb').read(), content_type='image/jpeg')

    # --- GET Request Tests ---

    def test_get_no_temp_booking_id_in_session(self):
        """
        Test GET request when 'current_temp_booking_id' is not in session.
        Should redirect to inventory:all with an error message.
        """
        response = self.client.get(self.url, follow=True)
        self.assertRedirects(response, reverse('inventory:all'))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Your booking session has expired or is invalid. Please start again.")

    def test_get_invalid_temp_booking_id(self):
        """
        Test GET request with an invalid 'current_temp_booking_id' in session.
        Should return a 404.
        """
        session = self.client.session
        session['current_temp_booking_id'] = 99999 # Non-existent ID
        session.save()

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_get_no_inventory_settings(self):
        """
        Test GET request when no InventorySettings exist.
        Should redirect to inventory:all with an error message.
        """
        # Delete existing settings
        InventorySettings.objects.all().delete()
        self.assertFalse(InventorySettings.objects.exists()) # Verify deletion

        self._create_temp_booking_in_session(self.client) # Need a valid temp booking ID for the view to run

        response = self.client.get(self.url, follow=True)
        self.assertRedirects(response, reverse('inventory:all'))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Inventory settings are not configured. Please contact support.")

        # Recreate settings for other tests
        self.inventory_settings = InventorySettingsFactory(pk=1) # Recreate as singleton

    def test_get_success_unauthenticated_user(self):
        """
        Test successful GET request for an unauthenticated user.
        Should render the form with no pre-filled SalesProfile data.
        """
        temp_booking = self._create_temp_booking_in_session(self.client)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/step1_sales_profile.html')
        self.assertIn('sales_profile_form', response.context)
        self.assertIn('temp_booking', response.context)
        self.assertEqual(response.context['temp_booking'], temp_booking)
        self.assertIsNone(response.context['sales_profile_form'].instance.pk) # Should be an unsaved instance

    def test_get_success_authenticated_user_no_profile(self):
        """
        Test successful GET request for an authenticated user with no existing SalesProfile.
        Should render the form with no pre-filled SalesProfile data.
        """
        self.client.login(username='testuser', password='password123')
        temp_booking = self._create_temp_booking_in_session(self.client, user=self.user)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('sales_profile_form', response.context)
        self.assertIsNone(response.context['sales_profile_form'].instance.pk) # Still unsaved instance

    def test_get_success_authenticated_user_with_profile(self):
        """
        Test successful GET request for an authenticated user with an existing SalesProfile.
        Should pre-fill the form with the user's SalesProfile data.
        """
        self.client.login(username='testuser', password='password123')
        existing_profile = SalesProfileFactory(user=self.user, name='Existing Name', email='existing@example.com')
        temp_booking = self._create_temp_booking_in_session(self.client, user=self.user)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('sales_profile_form', response.context)
        self.assertEqual(response.context['sales_profile_form'].instance, existing_profile)
        self.assertEqual(response.context['sales_profile_form'].initial['name'], 'Existing Name')
        self.assertEqual(response.context['sales_profile_form'].initial['email'], 'existing@example.com')

    def test_get_success_temp_booking_has_profile(self):
        """
        Test GET request where temp_booking already has a sales_profile linked.
        This profile should be used for pre-filling.
        """
        existing_profile_for_temp = SalesProfileFactory(name='Temp Linked Name', email='temp_linked@example.com')
        temp_booking = self._create_temp_booking_in_session(self.client, sales_profile=existing_profile_for_temp)

        # Log in a different user, who has their own profile, to ensure temp_booking's profile takes precedence
        another_user = UserFactory(username='anotheruser', email='another@example.com')
        another_user.set_password('password123')
        another_user.save()
        SalesProfileFactory(user=another_user, name='Another User Profile', email='anotheruser@example.com')
        self.client.login(username='anotheruser', password='password123')

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('sales_profile_form', response.context)
        # Should use the profile linked to temp_booking, not the logged-in user's profile
        self.assertEqual(response.context['sales_profile_form'].instance, existing_profile_for_temp)
        self.assertEqual(response.context['sales_profile_form'].initial['name'], 'Temp Linked Name')
        self.assertEqual(response.context['sales_profile_form'].initial['email'], 'temp_linked@example.com')


    # --- POST Request Tests ---

    @mock.patch('django.contrib.messages.success')
    @mock.patch('django.contrib.messages.error')
    def test_post_no_temp_booking_id_in_session(self, mock_error, mock_success):
        """
        Test POST request when 'current_temp_booking_id' is not in session.
        Should redirect with an error message.
        """
        response = self.client.post(self.url, data={}, follow=True)
        self.assertRedirects(response, reverse('inventory:all'))
        mock_error.assert_called_once_with(mock.ANY, "Your booking session has expired or is invalid. Please start again.")
        mock_success.assert_not_called()

    @mock.patch('django.contrib.messages.success')
    @mock.patch('django.contrib.messages.error')
    def test_post_invalid_temp_booking_id(self, mock_error, mock_success):
        """
        Test POST request with an invalid 'current_temp_booking_id' in session.
        Should return a 404.
        """
        session = self.client.session
        session['current_temp_booking_id'] = 99999 # Non-existent ID
        session.save()

        response = self.client.post(self.url, data={'name': 'Test User'})
        self.assertEqual(response.status_code, 404)
        mock_error.assert_not_called()
        mock_success.assert_not_called()

    @mock.patch('django.contrib.messages.success')
    @mock.patch('django.contrib.messages.error')
    def test_post_no_inventory_settings(self, mock_error, mock_success):
        """
        Test POST request when no InventorySettings exist.
        Should redirect to inventory:all with an error message.
        """
        InventorySettings.objects.all().delete()
        self._create_temp_booking_in_session(self.client) # Need a valid temp booking ID

        response = self.client.post(self.url, data={'name': 'Test User'}, follow=True)
        self.assertRedirects(response, reverse('inventory:all'))
        mock_error.assert_called_once_with(mock.ANY, "Inventory settings are not configured. Please contact support.")
        mock_success.assert_not_called()

        # Recreate settings for other tests
        self.inventory_settings = InventorySettingsFactory(pk=1)


    @mock.patch('django.contrib.messages.success')
    @mock.patch('django.contrib.messages.error')
    def test_post_valid_data_new_profile_unauthenticated(self, mock_error, mock_success):
        """
        Test successful POST request for an unauthenticated user creating a new SalesProfile.
        """
        temp_booking = self._create_temp_booking_in_session(self.client)
        initial_profile_count = SalesProfile.objects.count()

        post_data = {
            'name': 'New Customer',
            'email': 'new@example.com',
            'phone_number': '0412345678',
            'date_of_birth': '1990-01-01',
            # Other required fields for SalesProfileForm if any are set as required by InventorySettings
        }
        response = self.client.post(self.url, data=post_data, follow=True)

        self.assertRedirects(response, reverse('inventory:booking_details_and_appointment'))
        mock_success.assert_called_once_with(mock.ANY, "Personal details saved. Proceed to booking details and appointment.")
        mock_error.assert_not_called()

        self.assertEqual(SalesProfile.objects.count(), initial_profile_count + 1)
        new_profile = SalesProfile.objects.latest('created_at') # Get the newly created profile
        self.assertEqual(new_profile.name, 'New Customer')
        self.assertEqual(new_profile.email, 'new@example.com')
        self.assertIsNone(new_profile.user) # Should not be linked to a user

        # Verify TempSalesBooking is updated
        temp_booking.refresh_from_db()
        self.assertEqual(temp_booking.sales_profile, new_profile)

    @mock.patch('django.contrib.messages.success')
    @mock.patch('django.contrib.messages.error')
    def test_post_valid_data_update_existing_profile_authenticated(self, mock_error, mock_success):
        """
        Test successful POST request for an authenticated user updating their existing SalesProfile.
        """
        self.client.login(username='testuser', password='password123')
        existing_profile = SalesProfileFactory(user=self.user, name='Old Name', email='old@example.com', phone_number='111')
        temp_booking = self._create_temp_booking_in_session(self.client, user=self.user, sales_profile=existing_profile)
        initial_profile_count = SalesProfile.objects.count()

        post_data = {
            'name': 'Updated Name',
            'email': 'updated@example.com',
            'phone_number': '0498765432',
            'date_of_birth': '1985-05-05',
        }
        response = self.client.post(self.url, data=post_data, follow=True)

        self.assertRedirects(response, reverse('inventory:booking_details_and_appointment'))
        mock_success.assert_called_once_with(mock.ANY, "Personal details saved. Proceed to booking details and appointment.")
        mock_error.assert_not_called()

        self.assertEqual(SalesProfile.objects.count(), initial_profile_count) # No new profile created
        existing_profile.refresh_from_db()
        self.assertEqual(existing_profile.name, 'Updated Name')
        self.assertEqual(existing_profile.email, 'updated@example.com')
        self.assertEqual(existing_profile.user, self.user) # Should still be linked

        temp_booking.refresh_from_db()
        self.assertEqual(temp_booking.sales_profile, existing_profile) # TempBooking still linked to updated profile

    @mock.patch('django.contrib.messages.success')
    @mock.patch('django.contrib.messages.error')
    def test_post_invalid_data(self, mock_error, mock_success):
        """
        Test POST request with invalid form data.
        Should re-render the form with errors and an error message.
        """
        temp_booking = self._create_temp_booking_in_session(self.client)
        initial_profile_count = SalesProfile.objects.count()

        # Invalid data: missing required 'name' and invalid email format
        post_data = {
            'name': '', # Missing name
            'email': 'invalid-email',
            'phone_number': '0412345678',
            'date_of_birth': '1990-01-01',
        }
        response = self.client.post(self.url, data=post_data)

        self.assertEqual(response.status_code, 200) # Should re-render the page
        self.assertTemplateUsed(response, 'inventory/step1_sales_profile.html')
        mock_error.assert_called_once_with(mock.ANY, "Please correct the errors below.")
        mock_success.assert_not_called()

        self.assertEqual(SalesProfile.objects.count(), initial_profile_count) # No new profile should be created

        # Check if form errors are present in the context
        self.assertIn('sales_profile_form', response.context)
        form = response.context['sales_profile_form']
        self.assertIn('name', form.errors)
        self.assertIn('email', form.errors)

    @mock.patch('django.contrib.messages.success')
    @mock.patch('django.contrib.messages.error')
    def test_post_requires_drivers_license(self, mock_error, mock_success):
        """
        Test POST request when InventorySettings requires a driver's license.
        """
        self.inventory_settings.require_drivers_license = True
        self.inventory_settings.save()

        temp_booking = self._create_temp_booking_in_session(self.client)

        # Valid data, but missing required license fields
        post_data_missing_license = {
            'name': 'License Required',
            'email': 'license@example.com',
            'phone_number': '0412345678',
            'date_of_birth': '1990-01-01',
        }
        response = self.client.post(self.url, data=post_data_missing_license)
        self.assertEqual(response.status_code, 200)
        form = response.context['sales_profile_form']
        self.assertIn('drivers_license_number', form.errors)
        self.assertIn('drivers_license_expiry', form.errors)
        self.assertIn('drivers_license_image', form.errors) # Assuming image is also required

        # Valid data with license info and dummy image
        with self._create_dummy_image() as dummy_image:
            post_data_with_license = {
                'name': 'License Provided',
                'email': 'license_ok@example.com',
                'phone_number': '0412345678',
                'date_of_birth': '1990-01-01',
                'drivers_license_number': '12345ABC',
                'drivers_license_expiry': '2030-12-31',
            }
            files = {'drivers_license_image': dummy_image}
            response = self.client.post(self.url, data=post_data_with_license, files=files, follow=True)

            self.assertRedirects(response, reverse('inventory:booking_details_and_appointment'))
            mock_success.assert_called_once_with(mock.ANY, "Personal details saved. Proceed to booking details and appointment.")
            mock_error.assert_not_called()
            
            new_profile = SalesProfile.objects.latest('created_at')
            self.assertEqual(new_profile.drivers_license_number, '12345ABC')
            self.assertIsNotNone(new_profile.drivers_license_image)

        # Clean up dummy image file
        if os.path.exists(dummy_image.name):
            os.remove(dummy_image.name)


    @mock.patch('django.contrib.messages.success')
    @mock.patch('django.contrib.messages.error')
    def test_post_requires_address_info(self, mock_error, mock_success):
        """
        Test POST request when InventorySettings requires address information.
        """
        self.inventory_settings.require_address_info = True
        self.inventory_settings.save()

        temp_booking = self._create_temp_booking_in_session(self.client)

        # Valid data, but missing required address fields
        post_data_missing_address = {
            'name': 'Address Required',
            'email': 'address@example.com',
            'phone_number': '0412345678',
            'date_of_birth': '1990-01-01',
        }
        response = self.client.post(self.url, data=post_data_missing_address)
        self.assertEqual(response.status_code, 200)
        form = response.context['sales_profile_form']
        self.assertIn('address_line_1', form.errors)
        self.assertIn('city', form.errors)
        self.assertIn('post_code', form.errors)
        self.assertIn('state', form.errors)
        self.assertIn('country', form.errors)

        # Valid data with address info
        post_data_with_address = {
            'name': 'Address Provided',
            'email': 'address_ok@example.com',
            'phone_number': '0412345678',
            'date_of_birth': '1990-01-01',
            'address_line_1': '123 Main St',
            'city': 'Sydney',
            'state': 'NSW',
            '' 'post_code': '2000',
            'country': 'AU',
        }
        response = self.client.post(self.url, data=post_data_with_address, follow=True)

        self.assertRedirects(response, reverse('inventory:booking_details_and_appointment'))
        mock_success.assert_called_once_with(mock.ANY, "Personal details saved. Proceed to booking details and appointment.")
        mock_error.assert_not_called()

        new_profile = SalesProfile.objects.latest('created_at')
        self.assertEqual(new_profile.address_line_1, '123 Main St')
        self.assertEqual(new_profile.city, 'Sydney')
        self.assertEqual(new_profile.country, 'AU')

