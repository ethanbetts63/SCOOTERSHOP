from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.messages import get_messages
from django.contrib.messages.storage.fallback import FallbackStorage
import datetime
import uuid
from unittest.mock import patch, Mock
from django.core.files.uploadedfile import SimpleUploadedFile

# Import the view to be tested
from service.views.v2_views.user_views import Step3CustomerMotorcycleView
from service.forms import CustomerMotorcycleForm

# Import models and factories
from service.models import TempServiceBooking, ServiceProfile, CustomerMotorcycle, ServiceType, ServiceSettings, ServiceBrand # Import ServiceBrand
from ..test_helpers.model_factories import (
    UserFactory,
    ServiceProfileFactory,
    TempServiceBookingFactory,
    CustomerMotorcycleFactory,
    ServiceTypeFactory,
    ServiceSettingsFactory,
)


class Step3CustomerMotorcycleViewTest(TestCase):
    """
    Tests for the Step3CustomerMotorcycleView (dispatch, GET, and POST methods).
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up common data for all tests in this class.
        """
        cls.factory = RequestFactory()
        cls.user = UserFactory()
        cls.service_type = ServiceTypeFactory()
        cls.base_url = reverse('service:service_book_step3')
        
        # Ensure a ServiceSettings instance exists for tests that rely on it
        cls.service_settings = ServiceSettingsFactory(
            enable_service_brands=True,
            other_brand_policy_text="Policy for 'Other' brand."
        )

        # --- IMPORTANT FIX: Create ServiceBrand instances for tests ---
        # These brands must exist in the database for the ChoiceField to validate them.
        cls.honda_brand = ServiceBrand.objects.create(name='Honda')
        cls.yamaha_brand = ServiceBrand.objects.create(name='Yamaha')
        cls.sym_brand = ServiceBrand.objects.create(name='sym')
        cls.vespa_brand = ServiceBrand.objects.create(name='vespa')


    def setUp(self):
        """
        Set up for each test method. Ensure a clean state and common request setup.
        """
        TempServiceBooking.objects.all().delete()
        CustomerMotorcycle.objects.all().delete()
        ServiceProfile.objects.all().delete() # Clean up ServiceProfiles as they might be created/linked

        # This will be the ServiceProfile that gets linked to the TempServiceBooking for authenticated users.
        self.auth_user_service_profile = ServiceProfileFactory(user=self.user)

        # Create a valid TempServiceBooking for tests.
        # For authenticated user tests, link to self.auth_user_service_profile.
        # For anonymous user tests, we will manually set service_profile=None.
        self.temp_booking = TempServiceBookingFactory(
            service_type=self.service_type,
            service_date=datetime.date.today() + datetime.timedelta(days=7), # A valid date
            customer_motorcycle=None, # Ensure it starts as None for add new tests
            service_profile=self.auth_user_service_profile # Default for authenticated tests
        )

        # Set the UUID in the client's session for tests using self.client
        # This will be overridden in specific anonymous tests.
        session = self.client.session
        session['temp_booking_uuid'] = str(self.temp_booking.session_uuid)
        session.save()


    # --- Dispatch Method Tests ---

    def test_dispatch_no_temp_booking_uuid_in_session(self):
        """
        Test dispatch redirects to service:service if 'temp_booking_uuid' is missing from session.
        """
        request = self.factory.get(self.base_url)
        request.session = {} # No UUID in session
        request.user = self.user # User doesn't matter for this check
        response = Step3CustomerMotorcycleView().dispatch(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('service:service'))

    def test_dispatch_invalid_temp_booking_uuid_in_session(self):
        """
        Test dispatch redirects to service:service if 'temp_booking_uuid' in session is invalid.
        """
        request = self.factory.get(self.base_url)
        request.session = {'temp_booking_uuid': str(uuid.uuid4())} # A valid UUID format, but not in DB
        request.user = self.user
        response = Step3CustomerMotorcycleView().dispatch(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('service:service'))
        self.assertNotIn('temp_booking_uuid', request.session) # Should remove invalid UUID from session

    def test_dispatch_valid_temp_booking_proceeds(self):
        """
        Test dispatch proceeds if a valid temp_booking_uuid is in session.
        It should return an HttpResponse from the GET method after successful dispatch.
        """
        request = self.factory.get(self.base_url)
        request.session = {'temp_booking_uuid': str(self.temp_booking.session_uuid)}
        request.user = self.user 
        
        # Manually attach session to request for dispatch to work
        view = Step3CustomerMotorcycleView()
        # Mock the get method that dispatch will call, so we can assert it was called.
        # This prevents the actual rendering and focuses on dispatch's behavior.
        with patch.object(view, 'get', return_value=Mock(spec=True, status_code=200)) as mock_get:
            response = view.dispatch(request)
            self.assertEqual(response.status_code, 200) # Assert it returns a success response (from mock_get)
            mock_get.assert_called_once_with(request, *(), **{}) # Assert get was called


    # --- GET Method Tests ---

    def test_get_renders_blank_form_when_no_motorcycle_linked(self):
        """
        Test GET request renders a blank CustomerMotorcycleForm when temp_booking.customer_motorcycle is None.
        """
        # Ensure temp_booking.customer_motorcycle is None (it is by default in setUp)
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'service/step3_customer_motorcycle.html')
        self.assertIsInstance(response.context['form'], CustomerMotorcycleForm)
        self.assertIsNone(response.context['form'].instance.pk) # Check that it's a new instance
        self.assertEqual(response.context['temp_booking'], self.temp_booking)
        self.assertEqual(response.context['other_brand_policy_text'], self.service_settings.other_brand_policy_text)
        self.assertEqual(response.context['enable_service_brands'], self.service_settings.enable_service_brands)
        self.assertEqual(response.context['step'], 3)
        self.assertEqual(response.context['total_steps'], 7)

    def test_get_renders_prefilled_form_when_motorcycle_linked(self):
        """
        Test GET request renders a pre-filled CustomerMotorcycleForm when temp_booking has a linked motorcycle.
        """
        # Ensure the brand exists in the database for the form to pre-populate correctly
        existing_motorcycle = CustomerMotorcycleFactory(service_profile=self.auth_user_service_profile, brand=self.honda_brand.name)
        self.temp_booking.customer_motorcycle = existing_motorcycle
        self.temp_booking.save()

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'service/step3_customer_motorcycle.html')
        self.assertIsInstance(response.context['form'], CustomerMotorcycleForm)
        self.assertEqual(response.context['form'].instance, existing_motorcycle) # Check pre-filled instance


    # --- POST Method Tests (Add New Motorcycle) ---

    def test_post_add_new_motorcycle_valid_data_anonymous_user(self):
        """
        Test POST for adding a new motorcycle with valid data as an anonymous user.
        Ensures a new CustomerMotorcycle is created and linked to temp_booking,
        and its service_profile remains None as per current model design for anonymous.
        """
        # Set up for anonymous user
        self.client.logout() # Ensure no user is logged in (clears session, including temp_booking_uuid)
        
        # Re-set the temp_booking_uuid in the session AFTER logging out
        session = self.client.session
        session['temp_booking_uuid'] = str(self.temp_booking.session_uuid)
        session.save()

        self.temp_booking.service_profile = None # Explicitly ensure no profile is linked yet for anonymous
        self.temp_booking.save()

        post_data = {
            'brand': self.honda_brand.name, 
            'model': '600RR',
            'year': 2020,
            'engine_size': '600cc',
            'rego': 'ANON123',
            'vin_number': '12345678901234567', # 17 chars
            'odometer': 15000,
            'transmission': 'MANUAL',
            'engine_number': 'ENG123ABC',
        }
        response = self.client.post(self.base_url, post_data)
        
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('service:service_book_step4'))

        # Verify a new CustomerMotorcycle was created
        self.assertEqual(CustomerMotorcycle.objects.count(), 1)
        new_motorcycle = CustomerMotorcycle.objects.first()
        self.assertEqual(new_motorcycle.brand, self.honda_brand.name)
        self.assertIsNone(new_motorcycle.service_profile) # Should be None for anonymous at this stage

        # Verify temp_booking is linked to the new motorcycle
        self.temp_booking.refresh_from_db()
        self.assertEqual(self.temp_booking.customer_motorcycle, new_motorcycle)


    def test_post_add_new_motorcycle_valid_data_authenticated_user(self):
        """
        Test POST for adding a new motorcycle with valid data as an authenticated user.
        Ensures a new CustomerMotorcycle is created and linked to temp_booking and user's profile.
        """
        self.client.force_login(self.user) # Ensure logged in
        
        # temp_booking already linked to self.auth_user_service_profile in setUp

        post_data = {
            'brand': self.yamaha_brand.name, # Use a brand that exists in the database
            'model': 'R1',
            'year': 2022,
            'engine_size': '1000cc',
            'rego': 'AUTH456',
            'vin_number': '76543210987654321', # 17 chars
            'odometer': 5000,
            'transmission': 'MANUAL',
            'engine_number': 'ENG456DEF',
        }
        response = self.client.post(self.base_url, post_data)
        
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('service:service_book_step4'))

        self.assertEqual(CustomerMotorcycle.objects.count(), 1)
        new_motorcycle = CustomerMotorcycle.objects.first()
        self.assertEqual(new_motorcycle.brand, self.yamaha_brand.name)
        # Service profile should be linked for authenticated user
        self.assertEqual(new_motorcycle.service_profile, self.auth_user_service_profile)

        self.temp_booking.refresh_from_db()
        self.assertEqual(self.temp_booking.customer_motorcycle, new_motorcycle)

    def test_post_add_new_motorcycle_invalid_data(self):
        """
        Test POST for adding a new motorcycle with invalid data (e.g., missing required field).
        Should re-render the form with errors and not create a motorcycle.
        """
        # Missing 'brand' (which is now a required ChoiceField)
        post_data = {
            'model': '600RR',
            'year': 2020,
            'engine_size': '600cc',
            'rego': 'ANON123',
            'vin_number': '12345678901234567', # 17 chars
            'odometer': 15000,
            'transmission': 'MANUAL',
            'engine_number': 'ENG123ABC',
        }
        response = self.client.post(self.base_url, post_data)
        
        self.assertEqual(response.status_code, 200) # Should render the form again
        self.assertTemplateUsed(response, 'service/step3_customer_motorcycle.html')
        self.assertIn('form', response.context)
        self.assertFalse(response.context['form'].is_valid())
        self.assertIn('brand', response.context['form'].errors) # Check for a specific error

        self.assertEqual(CustomerMotorcycle.objects.count(), 0) # No motorcycle should be created
        self.temp_booking.refresh_from_db()
        self.assertIsNone(self.temp_booking.customer_motorcycle) # Temp booking should still have no motorcycle

    def test_post_add_new_motorcycle_other_brand_missing_name(self):
        """
        Test POST for adding a new motorcycle with 'Other' brand but missing other_brand_name.
        Should re-render the form with errors.
        """
        post_data = {
            'brand': 'Other', # This is now a valid choice
            'model': 'Bike',
            'year': 2023,
            'engine_size': '500cc',
            'rego': 'CUSTOM1',
            'vin_number': 'ABCDEF12345678901', # Corrected to 17 chars
            'odometer': 100,
            'transmission': 'AUTOMATIC',
            'engine_number': 'CUSTOMENG',
            # 'other_brand_name' is intentionally missing
        }
        response = self.client.post(self.base_url, post_data)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'service/step3_customer_motorcycle.html')
        self.assertIn('form', response.context)
        self.assertFalse(response.context['form'].is_valid())
        self.assertIn('other_brand_name', response.context['form'].errors)
        self.assertIn("Please specify the brand name when 'Other' is selected.", response.context['form'].errors['other_brand_name'])

        self.assertEqual(CustomerMotorcycle.objects.count(), 0)
        self.temp_booking.refresh_from_db()
        self.assertIsNone(self.temp_booking.customer_motorcycle)


    def test_post_add_new_motorcycle_other_brand_with_name(self):
        """
        Test POST for adding a new motorcycle with 'Other' brand and provided other_brand_name.
        Ensures the 'brand' field on the model is set to other_brand_name.
        """
        post_data = {
            'brand': 'Other',
            'other_brand_name': 'My Custom Brand',
            'model': 'Bike',
            'year': 2023,
            'engine_size': '500cc',
            'rego': 'CUSTOM1',
            'vin_number': 'ABCDEF12345678901', # Corrected to 17 chars
            'odometer': 100,
            'transmission': 'AUTOMATIC',
            'engine_number': 'CUSTOMENG',
        }
        response = self.client.post(self.base_url, post_data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('service:service_book_step4'))

        self.assertEqual(CustomerMotorcycle.objects.count(), 1)
        new_motorcycle = CustomerMotorcycle.objects.first()
        self.assertEqual(new_motorcycle.brand, 'My Custom Brand') # Should be set from other_brand_name
        self.temp_booking.refresh_from_db()
        self.assertEqual(self.temp_booking.customer_motorcycle, new_motorcycle)


    # --- POST Method Tests (Edit Existing Motorcycle) ---

    def test_post_edit_existing_motorcycle_valid_data(self):
        """
        Test POST for editing an existing motorcycle with valid data.
        Ensures the existing motorcycle is updated and temp_booking link remains.
        """
        # Ensure the existing motorcycle's brand is one that exists in the database
        existing_motorcycle = CustomerMotorcycleFactory(
            service_profile=self.auth_user_service_profile, # Ensure it belongs to the user
            brand=self.sym_brand.name, # Use an existing brand
            model='OldModel', year=2000
        )
        self.temp_booking.customer_motorcycle = existing_motorcycle
        self.temp_booking.save()

        updated_year = existing_motorcycle.year + 1
        post_data = {
            'brand': existing_motorcycle.brand, # Use the existing valid brand name
            'model': existing_motorcycle.model,
            'year': updated_year, # Change a field
            'engine_size': existing_motorcycle.engine_size,
            'rego': existing_motorcycle.rego,
            'vin_number': existing_motorcycle.vin_number,
            'odometer': existing_motorcycle.odometer,
            'transmission': existing_motorcycle.transmission,
            'engine_number': existing_motorcycle.engine_number,
        }
        response = self.client.post(self.base_url, post_data)
        
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('service:service_book_step4'))

        # Verify the existing motorcycle was updated
        existing_motorcycle.refresh_from_db()
        self.assertEqual(existing_motorcycle.year, updated_year) # Check the updated field
        self.assertEqual(CustomerMotorcycle.objects.count(), 1) # No new motorcycle should be created

        # Verify temp_booking still linked to the same motorcycle
        self.temp_booking.refresh_from_db()
        self.assertEqual(self.temp_booking.customer_motorcycle, existing_motorcycle)

    def test_post_edit_existing_motorcycle_invalid_data(self):
        """
        Test POST for editing an existing motorcycle with invalid data.
        Should re-render the form with errors and not alter the existing motorcycle.
        """
        existing_motorcycle = CustomerMotorcycleFactory(
            service_profile=self.auth_user_service_profile,
            brand=self.vespa_brand.name, # Use an existing brand
        )
        self.temp_booking.customer_motorcycle = existing_motorcycle
        self.temp_booking.save()

        # Invalid data: 'year' in future
        post_data = {
            'brand': existing_motorcycle.brand, # Use the existing valid brand name
            'model': existing_motorcycle.model,
            'year': datetime.date.today().year + 5, # Invalid year
            'engine_size': existing_motorcycle.engine_size,
            'rego': existing_motorcycle.rego,
            'vin_number': existing_motorcycle.vin_number,
            'odometer': existing_motorcycle.odometer,
            'transmission': existing_motorcycle.transmission,
            'engine_number': existing_motorcycle.engine_number,
        }
        response = self.client.post(self.base_url, post_data)
        
        self.assertEqual(response.status_code, 200) # Should render the form again
        self.assertTemplateUsed(response, 'service/step3_customer_motorcycle.html')
        self.assertIn('form', response.context)
        self.assertFalse(response.context['form'].is_valid())
        self.assertIn('year', response.context['form'].errors)

        # Verify existing motorcycle was NOT updated
        existing_motorcycle.refresh_from_db()
        self.assertNotEqual(existing_motorcycle.year, datetime.date.today().year + 5) # Should still be 2000

        # Verify temp_booking still linked to the same motorcycle
        self.temp_booking.refresh_from_db()
        self.assertEqual(self.temp_booking.customer_motorcycle, existing_motorcycle)
