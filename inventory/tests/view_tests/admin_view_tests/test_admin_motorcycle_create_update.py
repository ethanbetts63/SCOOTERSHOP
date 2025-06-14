from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from io import BytesIO
from PIL import Image

from inventory.models import Motorcycle, MotorcycleCondition, MotorcycleImage

# Import factories from your test helpers
from ...test_helpers.model_factories import UserFactory, MotorcycleFactory, MotorcycleConditionFactory, MotorcycleImageFactory

class MotorcycleCreateUpdateViewTest(TestCase):
    """
    Tests for the MotorcycleCreateUpdateView, covering creation, updates,
    and handling of primary and additional images.
    """
    @classmethod
    def setUpTestData(cls):
        """Set up data for the entire test case."""
        # Create an admin user who can access the views
        cls.admin_user = UserFactory(is_staff=True, is_superuser=True)
        # Create a regular user for permission testing (optional but good practice)
        cls.regular_user = UserFactory()

        # Pre-create conditions that the form might need
        MotorcycleConditionFactory(name='new', display_name='New')
        MotorcycleConditionFactory(name='used', display_name='Used')
        MotorcycleConditionFactory(name='demo', display_name='Demo')
        
        # Create a motorcycle instance for update tests
        cls.motorcycle_to_update = MotorcycleFactory(
            brand="Honda", model="CBR500R", year=2022, stock_number="UPDATE-001"
        )
        # Add some existing images to it
        MotorcycleImageFactory(motorcycle=cls.motorcycle_to_update)
        cls.image_to_delete = MotorcycleImageFactory(motorcycle=cls.motorcycle_to_update)

        cls.client = Client()

    def setUp(self):
        """Login the admin user before each test."""
        self.client.login(username=self.admin_user.username, password='password') # Assuming default password if not set in factory

    @staticmethod
    def _create_dummy_image(name='dummy.png'):
        """Creates an in-memory image file for testing uploads."""
        file = BytesIO()
        image = Image.new('RGB', (100, 100), color='blue')
        image.save(file, 'png')
        file.name = name
        file.seek(0)
        return SimpleUploadedFile(name=file.name, content=file.read(), content_type='image/png')

    def test_create_motorcycle_view_get(self):
        """Test GET request to the create motorcycle page."""
        response = self.client.get(reverse('inventory:admin_motorcycle_create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/admin_motorcycle_create_update.html')
        self.assertIn('form', response.context)
        self.assertIn('image_formset', response.context)

    def test_create_motorcycle_success(self):
        """
        Test successful creation of a new motorcycle with a primary image
        and multiple additional images.
        """
        self.assertEqual(Motorcycle.objects.count(), 1)
        self.assertEqual(MotorcycleImage.objects.count(), 2)

        condition_used = MotorcycleCondition.objects.get(name='used')
        
        post_data = {
            'brand': 'Kawasaki',
            'model': 'Ninja 400',
            'year': 2023,
            'price': 8500.00,
            'odometer': 150,
            'engine_size': 399,
            'transmission': 'manual',
            'stock_number': 'NEW-00123',
            'is_available': True,
            'conditions': [condition_used.pk],
        }
        
        # Prepare file uploads
        files = {
            'image': self._create_dummy_image('primary.png'),
            'additional_images': [
                self._create_dummy_image('additional1.png'),
                self._create_dummy_image('additional2.png')
            ]
        }

        response = self.client.post(reverse('inventory:admin_motorcycle_create'), data=post_data, files=files)

        # Check for successful redirection
        self.assertEqual(response.status_code, 302, "Expected a redirect after successful creation.")
        
        # Verify the motorcycle was created
        self.assertEqual(Motorcycle.objects.count(), 2)
        new_motorcycle = Motorcycle.objects.get(stock_number='NEW-00123')
        self.assertEqual(new_motorcycle.brand, 'Kawasaki')
        self.assertTrue(new_motorcycle.image.name.endswith('primary.png'))
        
        # Verify the additional images were created and linked
        self.assertEqual(MotorcycleImage.objects.count(), 4) # 2 old + 2 new
        self.assertEqual(new_motorcycle.images.count(), 2)
        self.assertTrue(any(img.image.name.endswith('additional1.png') for img in new_motorcycle.images.all()))
        self.assertTrue(any(img.image.name.endswith('additional2.png') for img in new_motorcycle.images.all()))

    def test_update_motorcycle_success(self):
        """
        Test successful update of an existing motorcycle, including deleting one
        image and adding another.
        """
        # Formset data needs a prefix, management form, and data for each form
        image_formset_data = {
            'images-TOTAL_FORMS': '2',
            'images-INITIAL_FORMS': '2',
            'images-MIN_NUM_FORMS': '0',
            'images-MAX_NUM_FORMS': '1000',
            # Mark one image for deletion
            f'images-1-id': self.image_to_delete.id,
            f'images-1-DELETE': 'on',
        }

        post_data = {
            'brand': 'Honda',
            'model': 'CBR500R ABS', # Updated model
            'year': 2022,
            'price': 12500.00, # Updated price
            'odometer': self.motorcycle_to_update.odometer,
            'engine_size': self.motorcycle_to_update.engine_size,
            'transmission': self.motorcycle_to_update.transmission,
            'stock_number': 'UPDATE-001',
            'is_available': True,
            'conditions': [MotorcycleCondition.objects.get(name='used').pk],
            **image_formset_data
        }

        files = {
            'additional_images': [self._create_dummy_image('new_additional.png')]
        }

        response = self.client.post(
            reverse('inventory:admin_motorcycle_update', kwargs={'pk': self.motorcycle_to_update.pk}),
            data=post_data,
            files=files
        )

        self.assertEqual(response.status_code, 302, "Expected a redirect after successful update.")
        
        # Refresh the instance from the database and check updates
        self.motorcycle_to_update.refresh_from_db()
        self.assertEqual(self.motorcycle_to_update.model, 'CBR500R ABS')
        self.assertEqual(self.motorcycle_to_update.price, 12500.00)
        
        # Check that one image was deleted and one was added
        # Initial: 2 images. Deleted: 1. Added: 1. Final: 2 images.
        self.assertEqual(self.motorcycle_to_update.images.count(), 2)
        # Check that the correct image was deleted
        self.assertFalse(MotorcycleImage.objects.filter(pk=self.image_to_delete.pk).exists())
        # Check that the new image was added
        self.assertTrue(self.motorcycle_to_update.images.filter(image__endswith='new_additional.png').exists())
