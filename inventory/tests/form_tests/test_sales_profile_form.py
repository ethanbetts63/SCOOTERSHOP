# inventory/tests/form_tests/test_sales_profile_form.py

from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from datetime import date, timedelta
from io import BytesIO # To simulate image file
from PIL import Image # For creating dummy image files

from inventory.forms import SalesProfileForm
from inventory.models import SalesProfile, InventorySettings
from ..test_helpers.model_factories import UserFactory, SalesProfileFactory, InventorySettingsFactory

class SalesProfileFormTest(TestCase):
    """
    Tests for the SalesProfileForm, focusing on conditional validation
    based on InventorySettings.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up common data for all tests in this class.
        """
        # Create a default InventorySettings instance (singleton pattern)
        cls.inventory_settings_default = InventorySettingsFactory()

        # Create an InventorySettings instance where address info is required
        cls.inventory_settings_address_required = InventorySettingsFactory(
            require_address_info=True,
            require_drivers_license=False, # Ensure only address is required
            pk=2 # Use a different PK if default already exists with PK 1
        )
        # Manually ensure singleton constraint is not violated for testing purposes,
        # or mock the InventorySettings.objects.first() call in the form's init
        # For simplicity, we're assuming factories create unique instances for testing
        # or that in tests, multiple instances are okay as long as `objects.first()`
        # returns the intended one. For form init, we explicitly pass the desired settings.

        # Create an InventorySettings instance where driver's license info is required
        cls.inventory_settings_dl_required = InventorySettingsFactory(
            require_address_info=False, # Ensure only DL is required
            require_drivers_license=True,
            pk=3
        )

        # Create an InventorySettings instance where both are required
        cls.inventory_settings_all_required = InventorySettingsFactory(
            require_address_info=True,
            require_drivers_license=True,
            pk=4
        )

        # Create a dummy image for drivers_license_image field
        cls.dummy_image_file = cls._create_dummy_image()

    @classmethod
    def tearDownClass(cls):
        """
        Clean up after all tests in this class.
        """
        # Close the dummy image file
        cls.dummy_image_file.close()
        super().tearDownClass()

    @staticmethod
    def _create_dummy_image(filename='test_license.png'):
        """Creates a dummy in-memory image file for testing."""
        file = BytesIO()
        image = Image.new('RGB', (100, 100), color = 'red')
        image.save(file, 'png')
        file.name = filename
        file.seek(0)
        return SimpleUploadedFile(name=filename, content=file.read(), content_type='image/png')


    def get_valid_data(self, include_address=True, include_dl=True):
        """Returns a dictionary of valid form data."""
        data = {
            'name': 'John Doe',
            'email': 'john.doe@example.com',
            'phone_number': '1234567890',
        }
        if include_address:
            data.update({
                'address_line_1': '123 Main St',
                'address_line_2': '',
                'city': 'Anytown',
                'state': 'AS',
                'post_code': '12345',
                'country': 'US',
            })
        if include_dl:
            data.update({
                'drivers_license_number': 'DL1234567',
                'drivers_license_expiry': (date.today() + timedelta(days=365)).isoformat(), # Future date
                'date_of_birth': (date.today() - timedelta(days=365*20)).isoformat(), # 20 years ago
            })
        return data

    def test_form_initialization_with_user_and_existing_sales_profile(self):
        """
        Test that the form pre-fills fields if a user with an existing SalesProfile
        is passed and the form is not bound.
        """
        user = UserFactory()
        existing_profile = SalesProfileFactory(
            user=user,
            name='Existing User',
            email='existing@example.com',
            phone_number='9876543210',
            address_line_1='456 Old St',
            city='Oldtown',
            post_code='54321',
            country='CA',
        )

        # Create an unbound form with the user
        form = SalesProfileForm(user=user)

        self.assertEqual(form.initial['name'], existing_profile.name)
        self.assertEqual(form.initial['email'], existing_profile.email)
        self.assertEqual(form.initial['phone_number'], existing_profile.phone_number)
        self.assertEqual(form.initial['address_line_1'], existing_profile.address_line_1)
        self.assertEqual(form.initial['city'], existing_profile.city)

        # Test with a bound form (initial should not override bound data)
        # We need valid data here since clean() will be called internally by is_valid()
        bound_data = self.get_valid_data(include_address=False, include_dl=False)
        bound_data.update({'name': 'New Name', 'email': 'new@example.com'})

        form_bound = SalesProfileForm(data=bound_data, user=user)
        
        # IMPORTANT: Call is_valid() before accessing cleaned_data
        self.assertTrue(form_bound.is_valid(), form_bound.errors.as_json())
        self.assertEqual(form_bound.cleaned_data.get('name'), 'New Name')
        self.assertEqual(form_bound.cleaned_data.get('email'), 'new@example.com')


    def test_form_initialization_no_user(self):
        """Test form initializes without a user."""
        form = SalesProfileForm()
        self.assertIsNone(form.user)
        self.assertFalse(form.is_bound)

    def test_form_initialization_user_no_sales_profile(self):
        """Test form initializes with a user but no associated sales profile."""
        user = UserFactory()
        form = SalesProfileForm(user=user)
        self.assertIsNotNone(form.user)
        self.assertIsNone(form.initial.get('name')) # Should not prefill if no profile


    # --- Test cases with default InventorySettings (no address/DL required) ---
    def test_form_valid_data_default_settings(self):
        """
        Test form is valid when default required fields are met
        and no address/DL specific requirements are set.
        """
        data = self.get_valid_data(include_address=False, include_dl=False)
        form = SalesProfileForm(data=data, inventory_settings=self.inventory_settings_default)
        self.assertTrue(form.is_valid(), form.errors.as_json())

    def test_form_missing_required_data_default_settings(self):
        """
        Test form is invalid when basic required fields (name, email, phone) are missing.
        """
        data = {} # No data
        form = SalesProfileForm(data=data, inventory_settings=self.inventory_settings_default)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
        self.assertIn('email', form.errors)
        self.assertIn('phone_number', form.errors)


    # --- Test cases with require_address_info = True ---
    def test_form_valid_with_address_required(self):
        """
        Test form is valid when address info is required and provided.
        """
        data = self.get_valid_data(include_address=True, include_dl=False)
        form = SalesProfileForm(data=data, inventory_settings=self.inventory_settings_address_required)
        self.assertTrue(form.is_valid(), form.errors.as_json())

    def test_form_invalid_missing_address_when_required(self):
        """
        Test form is invalid when address info is required but not provided.
        """
        data = self.get_valid_data(include_address=False, include_dl=False)
        form = SalesProfileForm(data=data, inventory_settings=self.inventory_settings_address_required)
        self.assertFalse(form.is_valid())
        self.assertIn('address_line_1', form.errors)
        self.assertIn('city', form.errors)
        self.assertIn('post_code', form.errors)
        self.assertIn('country', form.errors)
        self.assertNotIn('drivers_license_number', form.errors) # Should not be required


    # --- Test cases with require_drivers_license = True ---
    def test_form_valid_with_dl_required(self):
        """
        Test form is valid when driver's license info is required and provided.
        """
        data = self.get_valid_data(include_address=False, include_dl=True)
        files = {'drivers_license_image': self._create_dummy_image('test_license_2.png')}
        form = SalesProfileForm(data=data, files=files, inventory_settings=self.inventory_settings_dl_required)
        self.assertTrue(form.is_valid(), form.errors.as_json())

    def test_form_invalid_missing_dl_number_when_required(self):
        """
        Test form is invalid when driver's license number is required but not provided.
        """
        data = self.get_valid_data(include_address=False, include_dl=False) # Exclude DL data
        files = {'drivers_license_image': self._create_dummy_image('test_license_3.png')}
        form = SalesProfileForm(data=data, files=files, inventory_settings=self.inventory_settings_dl_required)
        self.assertFalse(form.is_valid())
        self.assertIn('drivers_license_number', form.errors)
        self.assertIn('drivers_license_expiry', form.errors)
        self.assertIn('date_of_birth', form.errors)
        self.assertNotIn('address_line_1', form.errors) # Should not be required

    def test_form_invalid_missing_dl_image_when_required(self):
        """
        Test form is invalid when driver's license image is required but not provided.
        """
        data = self.get_valid_data(include_address=False, include_dl=True)
        form = SalesProfileForm(data=data, inventory_settings=self.inventory_settings_dl_required) # No files
        self.assertFalse(form.is_valid())
        self.assertIn('drivers_license_image', form.errors)
        self.assertNotIn('drivers_license_number', form.errors) # Should be valid if provided


    # --- Test cases with both address and DL required ---
    def test_form_valid_with_all_required(self):
        """
        Test form is valid when both address and DL info are required and provided.
        """
        data = self.get_valid_data(include_address=True, include_dl=True)
        files = {'drivers_license_image': self._create_dummy_image('test_license_4.png')}
        form = SalesProfileForm(data=data, files=files, inventory_settings=self.inventory_settings_all_required)
        self.assertTrue(form.is_valid(), form.errors.as_json())

    def test_form_invalid_missing_some_address_and_dl_when_all_required(self):
        """
        Test form is invalid when both address and DL info are required,
        but some fields are missing.
        """
        data = { # Basic data, missing most address and DL
            'name': 'Jane Doe',
            'email': 'jane.doe@example.com',
            'phone_number': '0987654321',
        }
        form = SalesProfileForm(data=data, inventory_settings=self.inventory_settings_all_required)
        self.assertFalse(form.is_valid())
        self.assertIn('address_line_1', form.errors)
        self.assertIn('city', form.errors)
        self.assertIn('post_code', form.errors)
        self.assertIn('country', form.errors)
        self.assertIn('drivers_license_number', form.errors)
        self.assertIn('drivers_license_expiry', form.errors)
        self.assertIn('drivers_license_image', form.errors)
        self.assertIn('date_of_birth', form.errors)

    def test_form_missing_inventory_settings(self):
        """
        Test that the form behaves as if no requirements are set if
        inventory_settings is not passed during initialization.
        """
        data = self.get_valid_data(include_address=False, include_dl=False)
        form = SalesProfileForm(data=data) # No inventory_settings passed
        self.assertTrue(form.is_valid(), form.errors.as_json())

        # Now, test with a partial data set that would be invalid if settings were present
        data_missing_address = {
            'name': 'Test', 'email': 'test@example.com', 'phone_number': '123'
        }
        form_no_settings_missing_address = SalesProfileForm(data=data_missing_address)
        self.assertTrue(form_no_settings_missing_address.is_valid(), form_no_settings_missing_address.errors.as_json())
        # The clean method's conditional validation relies on self.inventory_settings being set.
        # If it's None, those checks are skipped. This confirms the desired fallback.
