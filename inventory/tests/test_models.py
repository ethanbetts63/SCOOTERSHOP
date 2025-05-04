# inventory/tests/test_models.py

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.urls import reverse 
from decimal import Decimal

# Import your models
from inventory.models import MotorcycleCondition, Motorcycle, MotorcycleImage
# Import the User model from your users app
from users.models import User # Assuming your custom user model is named User

import datetime 

# --- Tests for MotorcycleCondition Model ---
class MotorcycleConditionModelTest(TestCase):

    def test_condition_creation(self):
        """Test that a MotorcycleCondition can be created."""
        condition = MotorcycleCondition.objects.create(
            name='new',
            display_name='Brand New'
        )
        self.assertEqual(condition.name, 'new')
        self.assertEqual(condition.display_name, 'Brand New')
        self.assertEqual(str(condition), 'Brand New')

    def test_condition_name_is_unique(self):
        """Test that the 'name' field is unique."""
        MotorcycleCondition.objects.create(name='used', display_name='Second Hand')
        with self.assertRaises(IntegrityError):
            # Attempt to create another condition with the same name
            MotorcycleCondition.objects.create(name='used', display_name='Pre-owned')

    def test_condition_str_representation(self):
        """Test the __str__ method of MotorcycleCondition."""
        condition = MotorcycleCondition.objects.create(name='hire', display_name='For Hire')
        self.assertEqual(str(condition), 'For Hire')

# --- Tests for Motorcycle Model ---
class MotorcycleModelTest(TestCase):
    def setUp(self):
        """Set up test data."""
        # Create necessary MotorcycleCondition objects first
        self.new_condition = MotorcycleCondition.objects.create(name='new', display_name='New')
        self.used_condition = MotorcycleCondition.objects.create(name='used', display_name='Used')
        self.hire_condition = MotorcycleCondition.objects.create(name='hire', display_name='For Hire')
        self.demo_condition = MotorcycleCondition.objects.create(name='demo', display_name='Demonstration')


        # Create a test user (assuming your custom User model requires username and password)
        self.test_user = User.objects.create_user(username='testuser', password='testpassword')

        # Create a Motorcycle instance
        self.motorcycle = Motorcycle.objects.create(
            title='2022 Honda CBR500R',
            brand='Honda',
            model='CBR500R',
            year=2022,
            price=Decimal('7999.99'), # Import Decimal from decimal module if needed
            odometer=1500,
            engine_size='500cc',
            seats=2,
            transmission='manual',
            description='A great sport bike.',
            is_available=True,
            owner=self.test_user, # Assign the test user as owner
            # rego='ABC123', # Optional fields
            # rego_exp=datetime.date.today() + datetime.timedelta(days=365), # Optional fields
            # stock_number='H001', # Optional fields
            # daily_hire_rate=None, # Optional fields
        )
        # Add conditions after creation for ManyToManyField
        self.motorcycle.conditions.add(self.used_condition)


    def test_motorcycle_creation(self):
        """Test that a Motorcycle instance can be created."""
        # The instance is already created in setUp, just verify its attributes
        self.assertEqual(self.motorcycle.title, '2022 Honda CBR500R')
        self.assertEqual(self.motorcycle.brand, 'Honda')
        self.assertEqual(self.motorcycle.model, 'CBR500R')
        self.assertEqual(self.motorcycle.year, 2022)
        self.assertEqual(self.motorcycle.price, Decimal('7999.99'))
        self.assertEqual(self.motorcycle.odometer, 1500)
        self.assertEqual(self.motorcycle.engine_size, '500cc')
        self.assertEqual(self.motorcycle.seats, 2)
        self.assertEqual(self.motorcycle.transmission, 'manual')
        self.assertEqual(self.motorcycle.description, 'A great sport bike.')
        self.assertTrue(self.motorcycle.is_available)
        self.assertEqual(self.motorcycle.owner, self.test_user)
        self.assertIsNotNone(self.motorcycle.date_posted)
        self.assertTrue(self.motorcycle.conditions.filter(name='used').exists())
        self.assertFalse(self.motorcycle.conditions.filter(name='new').exists())

    def test_motorcycle_creation_with_optional_fields(self):
        """Test creating a Motorcycle with optional fields."""
        motorcycle_with_optionals = Motorcycle.objects.create(
            title='2023 Kawasaki Ninja 400',
            brand='Kawasaki',
            model='Ninja 400',
            year=2023,
            engine_size='400cc',
            seats=2,
            transmission='manual',
            description='Entry-level sport bike.',
            is_available=False, # Test setting is_available to False
            rego='XYZ789',
            rego_exp=datetime.date(2025, 12, 31),
            stock_number='K002',
            daily_hire_rate=Decimal('50.00'),
            weekly_hire_rate=Decimal('250.00'),
            monthly_hire_rate=Decimal('900.00'),
        )
        # Check optional fields
        self.assertEqual(motorcycle_with_optionals.rego, 'XYZ789')
        self.assertEqual(motorcycle_with_optionals.rego_exp, datetime.date(2025, 12, 31))
        self.assertEqual(motorcycle_with_optionals.stock_number, 'K002')
        self.assertEqual(motorcycle_with_optionals.daily_hire_rate, Decimal('50.00'))
        self.assertEqual(motorcycle_with_optionals.weekly_hire_rate, Decimal('250.00'))
        self.assertEqual(motorcycle_with_optionals.monthly_hire_rate, Decimal('900.00'))
        self.assertFalse(motorcycle_with_optionals.is_available) # Verify boolean field

    def test_motorcycle_str_representation(self):
        """Test the __str__ method of Motorcycle."""
        self.assertEqual(str(self.motorcycle), '2022 Honda CBR500R')

    def test_get_absolute_url(self):
        """Test the get_absolute_url method."""
        # This test requires the inventory app's urls to be set up and namespaced
        # Ensure your SCOOTER_SHOP/urls.py includes path('inventory/', include('inventory.urls', namespace='inventory'))
        # And inventory/urls.py has path('<int:pk>/', MotorcycleDetailView.as_view(), name='motorcycle-detail')
        expected_url = reverse('inventory:motorcycle-detail', kwargs={'pk': self.motorcycle.pk})
        self.assertEqual(self.motorcycle.get_absolute_url(), expected_url)

    def test_conditions_many_to_many(self):
        """Test adding and checking conditions."""
        self.motorcycle.conditions.add(self.hire_condition, self.new_condition)
        self.assertIn(self.used_condition, self.motorcycle.conditions.all())
        self.assertIn(self.hire_condition, self.motorcycle.conditions.all())
        self.assertIn(self.new_condition, self.motorcycle.conditions.all())
        self.assertEqual(self.motorcycle.conditions.count(), 3)

        self.motorcycle.conditions.remove(self.used_condition)
        self.assertNotIn(self.used_condition, self.motorcycle.conditions.all())
        self.assertEqual(self.motorcycle.conditions.count(), 2)

    def test_get_conditions_display_with_conditions(self):
        """Test get_conditions_display when using the M2M field."""
        self.motorcycle.conditions.add(self.new_condition, self.hire_condition)
        # Ensure conditions are sorted or handle order variability in test if necessary
        # For simplicity, let's just check for presence of expected strings
        display_string = self.motorcycle.get_conditions_display()
        self.assertIn('New', display_string)
        self.assertIn('For Hire', display_string)
        self.assertIn('Used', display_string) # Used was added in setUp

        # Check with only one condition
        self.motorcycle.conditions.clear()
        self.motorcycle.conditions.add(self.demo_condition)
        self.assertEqual(self.motorcycle.get_conditions_display(), 'Demonstration')


    def test_get_conditions_display_fallback(self):
        """Test get_conditions_display falling back to the old 'condition' field."""
        # Clear the new conditions field
        self.motorcycle.conditions.clear()
        # Set the old condition field
        self.motorcycle.condition = 'new' # Use one of the valid choices from CONDITION_CHOICES
        self.motorcycle.save()

        self.assertEqual(self.motorcycle.get_conditions_display(), 'New') # Check if it uses the display name

        # Test with a value not in CONDITION_CHOICES (it should just title case it)
        self.motorcycle.condition = 'unknown'
        self.motorcycle.save()
        self.assertEqual(self.motorcycle.get_conditions_display(), 'Unknown')

        # Test when neither is set
        self.motorcycle.condition = '' # Clear old field
        self.motorcycle.save()
        self.assertEqual(self.motorcycle.get_conditions_display(), 'N/A') # Check default return value


    def test_is_for_hire_method(self):
        """Test the is_for_hire method."""
        # Initially not for hire (only 'used' in setUp)
        self.assertFalse(self.motorcycle.is_for_hire())

        # Add the hire condition
        self.motorcycle.conditions.add(self.hire_condition)
        self.assertTrue(self.motorcycle.is_for_hire())

        # Remove the hire condition
        self.motorcycle.conditions.remove(self.hire_condition)
        self.assertFalse(self.motorcycle.is_for_hire())

    def test_transmission_choices(self):
        """Test that transmission field only accepts valid choices."""
        valid_transmissions = [choice[0] for choice in Motorcycle.TRANSMISSION_CHOICES]
        self.motorcycle.transmission = 'automatic'
        self.motorcycle.full_clean() # Use full_clean to trigger model validation
        self.motorcycle.save()
        self.assertEqual(self.motorcycle.transmission, 'automatic')

        with self.assertRaises(ValidationError):
            self.motorcycle.transmission = 'invalid_transmission'
            self.motorcycle.full_clean() # Should raise ValidationError

    # Add more tests here as needed for:
    # - price, daily_hire_rate, weekly_hire_rate, monthly_hire_rate fields (DecimalField properties)
    # - year, odometer, seats (IntegerField properties, min/max might be enforced by forms)
    # - vin_number, engine_number, rego, stock_number uniqueness/constraints if any beyond null/blank
    # - owner relationship (SET_NULL behavior on user deletion - requires deleting a user)
    # - FileField (image) - testing file uploads is more complex and often done with view tests or mocking

# --- Tests for MotorcycleImage Model ---

class MotorcycleImageModelTest(TestCase):

    def setUp(self):
        """Set up test data."""
        # Create a parent Motorcycle instance
        self.test_user = User.objects.create_user(username='testuser2', password='testpassword2')
        self.motorcycle = Motorcycle.objects.create(
            title='Test Bike for Image',
            brand='Test',
            model='ImageModel',
            year=2020,
            engine_size='250cc',
            seats=1,
            transmission='manual',
            description='A bike to test images.',
            is_available=True,
            owner=self.test_user,
        )
        # You would typically use Django's `SimpleUploadedFile` to mock image uploads
        # but for basic model creation test, just creating the instance is enough.
        # Testing file uploads themselves is usually done in view tests.

    def test_image_creation(self):
        """Test that a MotorcycleImage can be created and linked to a Motorcycle."""
        # Create a MotorcycleImage instance linked to the motorcycle
        # We'll use a dummy string for the file field path for this basic test
        # In a real test involving file storage, you'd use SimpleUploadedFile
        image = MotorcycleImage.objects.create(
            motorcycle=self.motorcycle,
            image='path/to/dummy/image.jpg' # Replace with SimpleUploadedFile for real file tests
        )

        self.assertEqual(image.motorcycle, self.motorcycle)
        self.assertEqual(image.image.name, 'path/to/dummy/image.jpg') # Check the stored path
        self.assertIsNotNone(image.pk) # Ensure the object was saved

        # Verify the image is accessible from the motorcycle's related_name
        self.assertEqual(self.motorcycle.images.count(), 1)
        self.assertEqual(self.motorcycle.images.first(), image)

    def test_image_str_representation(self):
        """Test the __str__ method of MotorcycleImage."""
        image = MotorcycleImage.objects.create(
             motorcycle=self.motorcycle,
             image='path/to/dummy/image.png'
         )
        self.assertEqual(str(image), f"Image for {self.motorcycle}")


    # Add tests for CASCADE delete - when a motorcycle is deleted, its images should be deleted
    def test_motorcycle_deletion_deletes_images(self):
        """Test that deleting a Motorcycle also deletes its associated MotorcycleImages."""
        image1 = MotorcycleImage.objects.create(motorcycle=self.motorcycle, image='img1.jpg')
        image2 = MotorcycleImage.objects.create(motorcycle=self.motorcycle, image='img2.png')

        self.assertEqual(self.motorcycle.images.count(), 2)
        self.assertEqual(MotorcycleImage.objects.count(), 2)

        # Delete the motorcycle
        motorcycle_pk = self.motorcycle.pk
        self.motorcycle.delete()

        # Check that the motorcycle is gone
        self.assertFalse(Motorcycle.objects.filter(pk=motorcycle_pk).exists())

        # Check that the associated images are also deleted
        self.assertEqual(MotorcycleImage.objects.count(), 0)
        self.assertFalse(MotorcycleImage.objects.filter(pk=image1.pk).exists())
        self.assertFalse(MotorcycleImage.objects.filter(pk=image2.pk).exists())

