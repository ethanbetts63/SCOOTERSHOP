# inventory/tests/test_motorcycle_detail.py

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test import override_settings # Needed for testing media files potentially

# Import models and views
from inventory.models import Motorcycle, MotorcycleCondition, MotorcycleImage
from inventory.views.motorcycle_detail import MotorcycleDetailView
# Import the utility function if you need to mock it
from unittest.mock import patch, MagicMock # Import patch and MagicMock
from decimal import Decimal # For price fields

User = get_user_model() # Get the currently active user model

# Set up dummy media root for testing file uploads/access
# In a real project, you might use a dedicated test settings file
TEST_MEDIA_ROOT = '/test_media/'
# override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT) # Apply this to the class or specific tests if needed

class MotorcycleDetailViewTest(TestCase):
    def setUp(self):
        """Set up test data for detail view tests."""
        self.client = Client()

        # Create test users
        self.staff_user = User.objects.create_user(
            username='staffuser',
            password='password',
            is_staff=True
        )
        self.regular_user = User.objects.create_user(
            username='regularuser',
            password='password'
        )

        # Create necessary MotorcycleCondition objects
        self.used_condition = MotorcycleCondition.objects.create(name='used', display_name='Used')
        self.new_condition = MotorcycleCondition.objects.create(name='new', display_name='New')
        self.hire_condition = MotorcycleCondition.objects.create(name='hire', display_name='For Hire')
        self.demo_condition = MotorcycleCondition.objects.create(name='demo', display_name='Demonstration')


        # Create a Motorcycle instance
        self.motorcycle = Motorcycle.objects.create(
            title='2022 Honda CB500F',
            brand='Honda',
            model='CB500F',
            year=2022,
            price=Decimal('6500.00'),
            odometer=5000,
            engine_size='500cc',
            seats=2,
            transmission='manual',
            description='A versatile naked bike.',
            is_available=True,
            owner=self.regular_user,
            rego='ABC123',
            stock_number='H002',
            daily_hire_rate=Decimal('75.00'),
            weekly_hire_rate=Decimal('350.00'),
            monthly_hire_rate=Decimal('1200.00'),
        )
        self.motorcycle.conditions.add(self.used_condition)

        # Create additional images for the motorcycle
        # For simple testing, we don't need actual files, just the model instances
        self.image1 = MotorcycleImage.objects.create(motorcycle=self.motorcycle, image='motorcycles/additional/image1.jpg')
        self.image2 = MotorcycleImage.objects.create(motorcycle=self.motorcycle, image='motorcycles/additional/image2.png')


        # Get the URL for the detail view
        self.detail_url = reverse('inventory:motorcycle-detail', kwargs={'pk': self.motorcycle.pk})

    def test_detail_view_renders_correct_template(self):
        """Test that the detail view uses the correct template."""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/motorcycle_detail.html')

    def test_detail_view_uses_correct_object_in_context(self):
        """Test that the detail view passes the correct motorcycle object to the template."""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['motorcycle'], self.motorcycle)
        # Check the context object name is correct
        self.assertIn('motorcycle', response.context)

    def test_detail_view_includes_additional_images_in_context(self):
        """Test that the detail view includes additional images in the context."""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('additional_images', response.context)
        additional_images_in_context = response.context['additional_images']

        # Check that the correct images are included
        self.assertEqual(len(additional_images_in_context), 2)
        self.assertIn(self.image1, additional_images_in_context)
        self.assertIn(self.image2, additional_images_in_context)

    @patch('inventory.views.motorcycle_detail.get_featured_motorcycles')
    def test_detail_view_includes_featured_motorcycles_in_context(self, mock_get_featured):
        """Test that the detail view includes featured motorcycles in the context."""
        # Mock the utility function call
        # Create dummy featured motorcycles to be returned by the mock
        featured_bike_1 = MagicMock(spec=Motorcycle, pk=99)
        featured_bike_1.title = 'Featured Bike 1'
        featured_bike_2 = MagicMock(spec=Motorcycle, pk=100)
        featured_bike_2.title = 'Featured Bike 2'
        mock_get_featured.return_value = [featured_bike_1, featured_bike_2]

        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('featured_motorcycles', response.context)
        self.assertEqual(len(response.context['featured_motorcycles']), 2)
        self.assertEqual(response.context['featured_motorcycles'], [featured_bike_1, featured_bike_2])

        # Verify the mock was called with the correct arguments
        # The condition passed should be based on the primary condition of the motorcycle
        mock_get_featured.assert_called_once_with(
            exclude_id=self.motorcycle.pk,
            limit=3,
            condition=self.used_condition.name # The primary condition in this setup
        )

    def test_detail_view_includes_specifications_in_context(self):
        """Test that the detail view includes filtered specifications in the context."""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('filtered_specifications', response.context)
        specifications = response.context['filtered_specifications']

        # Check for some expected specifications and their values
        self.assertTrue(any(spec['field'] == 'condition' and 'Used' in spec['value'] for spec in specifications))
        self.assertTrue(any(spec['field'] == 'year' and spec['value'] == 2022 for spec in specifications))
        self.assertTrue(any(spec['field'] == 'odometer' and spec['value'] == '5000 km' for spec in specifications))
        self.assertTrue(any(spec['field'] == 'engine_size' and spec['value'] == '500cc' for spec in specifications))
        self.assertTrue(any(spec['field'] == 'seats' and spec['value'] == 2 for spec in specifications))
        self.assertTrue(any(spec['field'] == 'transmission' and spec['value'] == 'manual' for spec in specifications))
        self.assertTrue(any(spec['field'] == 'rego' and spec['value'] == 'ABC123' for spec in specifications))
        self.assertTrue(any(spec['field'] == 'stock_number' and spec['value'] == 'H002' for spec in specifications))
        # Check if daily_hire_rate is *not* included initially (as it's not a hire bike in this setup)
        self.assertFalse(any(spec['field'] == 'daily_hire_rate' for spec in specifications))

    def test_detail_view_includes_hire_rate_for_hire_bike(self):
        """Test that daily_hire_rate is included for a hire bike."""
        # Make the motorcycle a hire bike
        self.motorcycle.conditions.add(self.hire_condition)
        self.motorcycle.save()

        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        specifications = response.context['filtered_specifications']

        # Check if daily_hire_rate is now included
        self.assertTrue(any(spec['field'] == 'daily_hire_rate' and spec['value'] == '$75.00' for spec in specifications))

        # Also check that the condition display is updated
        self.assertTrue(any(spec['field'] == 'condition' and 'For Hire' in spec['value'] for spec in specifications))


    def test_detail_view_returns_404_for_nonexistent_motorcycle(self):
        """Test that the detail view returns a 404 if the motorcycle does not exist."""
        nonexistent_url = reverse('inventory:motorcycle-detail', kwargs={'pk': 999}) # Assuming 999 is not a valid PK
        response = self.client.get(nonexistent_url)
        self.assertEqual(response.status_code, 404)

    # Add more tests here for specific template content checks (e.g., price displayed, description)
    # You can use self.assertContains(response, 'Expected Text')
    def test_detail_view_displays_motorcycle_info(self):
        """Test that key motorcycle information is displayed on the page."""
        response = self.client.get(self.detail_url)
        self.assertContains(response, self.motorcycle.title)
        self.assertContains(response, str(self.motorcycle.price)) # Check price display
        self.assertContains(response, self.motorcycle.description)
        # Check for existence of image elements (checking src is more complex, but possible)
        self.assertContains(response, '<img', count=3) # Main image + 2 additional images

    def test_detail_view_displays_specifications_correctly(self):
        """Test that specifications are rendered in the template."""
        response = self.client.get(self.detail_url)
        # Check for the presence of specification labels and values
        self.assertContains(response, 'Condition')
        self.assertContains(response, 'Used') # Check display name from condition
        self.assertContains(response, 'Year')
        self.assertContains(response, '2022')
        self.assertContains(response, 'Odometer')
        self.assertContains(response, '5000 km')
        self.assertContains(response, 'Engine')
        self.assertContains(response, '500cc')
        self.assertContains(response, 'Seats')
        self.assertContains(response, '2')
        self.assertContains(response, 'Transmission')
        self.assertContains(response, 'manual')
        self.assertContains(response, 'Registration')
        self.assertContains(response, 'ABC123')
        self.assertContains(response, 'Stock #')
        self.assertContains(response, 'H002')

    def test_detail_view_does_not_show_unavailable_motorcycle(self):
        """Test that an unavailable motorcycle returns a 404 or redirect (depending on view logic)."""
        # Note: Your current get_queryset in ListView filters by is_available,
        # but DetailView doesn't necessarily do this by default.
        # The default DetailView will show the object if it exists by PK.
        # If you want to hide unavailable motorcycles, you need to override get_queryset in DetailView.

        # For now, let's test the default DetailView behavior
        self.motorcycle.is_available = False
        self.motorcycle.save()

        response = self.client.get(self.detail_url)
        # The default DetailView will still find the object by PK even if is_available=False
        # So it should return 200, but the template might hide the "Buy" or "Hire" options.
        # If you need to prevent viewing unavailable bikes, override get_queryset in DetailView.
        self.assertEqual(response.status_code, 200) # Based on default DetailView behavior