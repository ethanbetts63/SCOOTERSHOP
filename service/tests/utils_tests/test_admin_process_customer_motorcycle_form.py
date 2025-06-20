from django.test import TestCase
from service.models import CustomerMotorcycle, ServiceProfile # Import ServiceProfile
from service.utils.admin_process_customer_motorcycle_form import admin_process_customer_motorcycle_form
from ..test_helpers.model_factories import ServiceProfileFactory, CustomerMotorcycleFactory, ServiceBrandFactory

class AdminProcessCustomerMotorcycleFormTest(TestCase):
    """
    Tests for the `admin_process_customer_motorcycle_form` utility function.
    This suite verifies that CustomerMotorcycle instances are created or updated correctly
    based on the input form data and associated ServiceProfile, specifically for the AdminCustomerMotorcycleForm.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up test data for all tests in this class.
        Create necessary related objects using factories.
        """
        cls.service_profile = ServiceProfileFactory()
        cls.another_service_profile = ServiceProfileFactory() # For testing linking
        cls.service_brand_honda = ServiceBrandFactory(name='Honda')
        cls.service_brand_yamaha = ServiceBrandFactory(name='Yamaha')

    def test_create_new_motorcycle_with_existing_brand(self):
        """
        Test successful creation of a new motorcycle with a brand typed in by the admin.
        This brand should exist in ServiceBrand, but the form simply takes a string.
        """
        post_data = {
            'service_profile': self.service_profile.pk, # Explicitly link a profile
            'brand': self.service_brand_honda.name,
            'model': 'CBR500R',
            'year': 2022,
            'engine_size': '500cc',
            'rego': 'ABC123',
            'odometer': 1500,
            'transmission': 'MANUAL',
            'vin_number': '12345678901234567',
            'engine_number': 'ENG12345',
        }
        files_data = {}

        form, motorcycle_instance = admin_process_customer_motorcycle_form(
            request_post_data=post_data,
            request_files=files_data,
            profile_instance=self.service_profile # This is used as fallback, but form's value takes precedence
        )

        self.assertTrue(form.is_valid())
        self.assertIsNotNone(motorcycle_instance)
        self.assertEqual(motorcycle_instance.service_profile, self.service_profile)
        self.assertEqual(motorcycle_instance.brand, post_data['brand'])
        self.assertEqual(motorcycle_instance.model, post_data['model'])
        self.assertEqual(motorcycle_instance.year, post_data['year'])
        self.assertEqual(CustomerMotorcycle.objects.count(), 1)


    def test_create_new_motorcycle_with_custom_brand_typed_in(self):
        """
        Test successful creation of a new motorcycle when a custom brand name
        (not in ServiceBrand) is typed directly into the brand field by the admin.
        """
        post_data = {
            'service_profile': self.service_profile.pk,
            'brand': 'Custom Chopper Brand', # Admin types this directly
            'model': 'Custom Build 1',
            'year': 2023,
            'engine_size': '1800cc',
            'rego': 'XYZ789',
            'odometer': 500,
            'transmission': 'MANUAL',
            'vin_number': 'ABCDEFGHIJKLMNOPQ',
            'engine_number': 'CUSTENG001',
        }
        files_data = {}

        form, motorcycle_instance = admin_process_customer_motorcycle_form(
            request_post_data=post_data,
            request_files=files_data,
            profile_instance=self.service_profile
        )

        self.assertTrue(form.is_valid())
        self.assertIsNotNone(motorcycle_instance)
        self.assertEqual(motorcycle_instance.service_profile, self.service_profile)
        # Assert that the brand is exactly what was typed in
        self.assertEqual(motorcycle_instance.brand, post_data['brand'])
        self.assertEqual(CustomerMotorcycle.objects.count(), 1)


    def test_update_existing_motorcycle_change_brand(self):
        """
        Test successful update of an existing motorcycle, changing its brand.
        """
        initial_motorcycle = CustomerMotorcycleFactory(
            service_profile=self.service_profile,
            brand=self.service_brand_honda.name,
            model='Old Model',
            year=2010,
            rego='OLD111',
            odometer=50000,
            transmission='MANUAL',
        )
        self.assertEqual(CustomerMotorcycle.objects.count(), 1)

        # Prepare update data to change brand to 'Yamaha' (from ServiceBrand)
        updated_post_data = {
            'service_profile': self.service_profile.pk, # Keep linked to same profile
            'brand': self.service_brand_yamaha.name,
            'model': 'FZ-07',
            'year': 2018,
            'engine_size': '689cc',
            'rego': 'NEW222',
            'odometer': 20000,
            'transmission': 'MANUAL',
            'vin_number': initial_motorcycle.vin_number,
            'engine_number': initial_motorcycle.engine_number,
        }
        files_data = {}

        form, updated_motorcycle_instance = admin_process_customer_motorcycle_form(
            request_post_data=updated_post_data,
            request_files=files_data,
            profile_instance=self.service_profile,
            motorcycle_id=initial_motorcycle.pk
        )

        self.assertTrue(form.is_valid())
        self.assertIsNotNone(updated_motorcycle_instance)
        self.assertEqual(updated_motorcycle_instance.pk, initial_motorcycle.pk)
        self.assertEqual(updated_motorcycle_instance.brand, updated_post_data['brand'])
        self.assertEqual(updated_motorcycle_instance.model, updated_post_data['model'])
        self.assertEqual(CustomerMotorcycle.objects.count(), 1)

    def test_update_existing_motorcycle_change_profile(self):
        """
        Test successful update of an existing motorcycle, changing its linked ServiceProfile.
        """
        initial_motorcycle = CustomerMotorcycleFactory(
            service_profile=self.service_profile,
            brand='Kawasaki',
            model='Ninja',
            year=2020,
            rego='OLDPROF',
            odometer=10000,
            transmission='MANUAL',
        )
        self.assertEqual(CustomerMotorcycle.objects.count(), 1)

        updated_post_data = {
            'service_profile': self.another_service_profile.pk, # Change linked profile
            'brand': 'Kawasaki', # Keep brand same
            'model': 'Ninja',
            'year': 2020,
            'engine_size': '600cc',
            'rego': 'NEWPROF',
            'odometer': 10500,
            'transmission': 'MANUAL',
            'vin_number': initial_motorcycle.vin_number,
            'engine_number': initial_motorcycle.engine_number,
        }
        files_data = {}

        form, updated_motorcycle_instance = admin_process_customer_motorcycle_form(
            request_post_data=updated_post_data,
            request_files=files_data,
            profile_instance=self.service_profile, # Original profile, but form value takes precedence
            motorcycle_id=initial_motorcycle.pk
        )

        self.assertTrue(form.is_valid())
        self.assertIsNotNone(updated_motorcycle_instance)
        self.assertEqual(updated_motorcycle_instance.pk, initial_motorcycle.pk)
        self.assertEqual(updated_motorcycle_instance.service_profile, self.another_service_profile)
        self.assertEqual(CustomerMotorcycle.objects.count(), 1)


    def test_form_invalid_missing_required_fields(self):
        """
        Test that the form is invalid if other required fields are missing.
        """
        post_data = {
            'service_profile': self.service_profile.pk,
            'brand': self.service_brand_honda.name,
            # 'model' is missing
            'year': 2022,
            'engine_size': '500cc',
            'rego': 'ABC123',
            'odometer': 1500,
            'transmission': 'MANUAL',
        }
        files_data = {}

        form, motorcycle_instance = admin_process_customer_motorcycle_form(
            request_post_data=post_data,
            request_files=files_data,
            profile_instance=self.service_profile
        )

        self.assertFalse(form.is_valid())
        self.assertIn('model', form.errors) # Expect 'model' to be a required field error
        self.assertIsNone(motorcycle_instance)
        self.assertEqual(CustomerMotorcycle.objects.count(), 0)

    def test_form_invalid_year_in_future(self):
        """
        Test that the form is invalid if the year is in the future.
        """
        from datetime import date
        future_year = date.today().year + 1

        post_data = {
            'service_profile': self.service_profile.pk,
            'brand': self.service_brand_honda.name,
            'model': 'Time Machine',
            'year': future_year, # Future year
            'engine_size': '1000cc',
            'rego': 'FUTURA',
            'odometer': 0,
            'transmission': 'MANUAL',
        }
        files_data = {}

        form, motorcycle_instance = admin_process_customer_motorcycle_form(
            request_post_data=post_data,
            request_files=files_data,
            profile_instance=self.service_profile
        )

        self.assertFalse(form.is_valid())
        self.assertIn('year', form.errors)
        self.assertIsNone(motorcycle_instance)

    def test_form_invalid_vin_number_length(self):
        """
        Test that the form is invalid if the VIN number is not 17 characters long.
        """
        post_data = {
            'service_profile': self.service_profile.pk,
            'brand': self.service_brand_honda.name,
            'model': 'Short VIN',
            'year': 2020,
            'engine_size': '500cc',
            'rego': 'SHORTY',
            'odometer': 1000,
            'transmission': 'MANUAL',
            'vin_number': 'TOO_SHORT', # Less than 17 chars
        }
        files_data = {}

        form, motorcycle_instance = admin_process_customer_motorcycle_form(
            request_post_data=post_data,
            request_files=files_data,
            profile_instance=self.service_profile
        )

        self.assertFalse(form.is_valid())
        self.assertIn('vin_number', form.errors)
        self.assertIsNone(motorcycle_instance)

    def test_form_invalid_negative_odometer(self):
        """
        Test that the form is invalid if the odometer reading is negative.
        """
        post_data = {
            'service_profile': self.service_profile.pk,
            'brand': self.service_brand_honda.name,
            'model': 'Negative Odometer',
            'year': 2020,
            'engine_size': '500cc',
            'rego': 'NEGATIV',
            'odometer': -100, # Negative odometer
            'transmission': 'MANUAL',
        }
        files_data = {}

        form, motorcycle_instance = admin_process_customer_motorcycle_form(
            request_post_data=post_data,
            request_files=files_data,
            profile_instance=self.service_profile
        )

        self.assertFalse(form.is_valid())
        self.assertIn('odometer', form.errors)
        self.assertIsNone(motorcycle_instance)

    def test_motorcycle_instance_not_found_with_form_error(self):
        """
        Test that the function returns (form, None) and the form is invalid
        if motorcycle_id is provided but no instance is found.
        (Reflects the added error message in the utility function)
        """
        post_data = {
            'service_profile': self.service_profile.pk,
            'brand': self.service_brand_honda.name,
            'model': 'NotFound',
            'year': 2020,
            'engine_size': '500cc',
            'rego': 'NOTFOUND',
            'odometer': 1000,
            'transmission': 'MANUAL',
        }
        files_data = {}

        # Try to update a non-existent motorcycle
        form, motorcycle_instance = admin_process_customer_motorcycle_form(
            request_post_data=post_data,
            request_files=files_data,
            profile_instance=self.service_profile,
            motorcycle_id=99999 # A non-existent ID
        )

        # The form should now be invalid because the utility function adds an error
        self.assertFalse(form.is_valid())
        self.assertIn('Selected motorcycle not found.', form.non_field_errors())
        self.assertIsNone(motorcycle_instance)
        # Verify no new motorcycle was created
        self.assertEqual(CustomerMotorcycle.objects.count(), 0)

