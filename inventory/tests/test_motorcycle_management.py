# inventory/tests/test_motorcycle_management.py

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile # For mocking file uploads
from django.db.models import signals # For potentially ignoring m2m signals if needed
from django.test import override_settings # For media root during tests
from django.contrib.messages import get_messages # To check messages
import tempfile # To create temporary files for uploads
import os # To join paths
import shutil # To remove temporary directories
import datetime # For date fields
from decimal import Decimal

# Import models, forms, and management views
from inventory.models import Motorcycle, MotorcycleCondition, MotorcycleImage
from inventory.forms import MotorcycleForm, MotorcycleImageFormSet
from inventory.views.motorcycle_detail import (
    MotorcycleCreateView,
    MotorcycleUpdateView,
    MotorcycleDeleteView,
)

User = get_user_model()

# Set up a temporary media root for testing file uploads
TEMP_MEDIA_ROOT = os.path.join(tempfile.gettempdir(), 'test_media')

@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class MotorcycleManagementViewTests(TestCase):
    def setUp(self):
        """Set up test data for management view tests."""
        self.client = Client()

        # Create test users with different permissions
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
        self.new_condition = MotorcycleCondition.objects.create(name='new', display_name='New')
        self.used_condition = MotorcycleCondition.objects.create(name='used', display_name='Used')
        self.hire_condition = MotorcycleCondition.objects.create(name='hire', display_name='For Hire')

        # Create a motorcycle instance for update/delete tests
        self.motorcycle_to_manage = Motorcycle.objects.create(
            title='2020 Ducati Monster 821', brand='Ducati', model='Monster 821', year=2020,
            price=Decimal('10000.00'), odometer=6000, engine_size='821cc', seats=2,
            transmission='manual', description='A fun naked bike.', is_available=True,
            owner=self.staff_user, # Owned by staff user for simpler permission tests
            stock_number='D001',
        )
        self.motorcycle_to_manage.conditions.add(self.used_condition)

        # URLs for the management views
        self.create_url = reverse('inventory:motorcycle-create')
        self.update_url = reverse('inventory:motorcycle-update', kwargs={'pk': self.motorcycle_to_manage.pk})
        self.delete_url = reverse('inventory:motorcycle-delete', kwargs={'pk': self.motorcycle_to_manage.pk})

    @classmethod
    def tearDownClass(cls):
        """Clean up temporary media directory after all tests."""
        super().tearDownClass()
        if os.path.exists(TEMP_MEDIA_ROOT):
            shutil.rmtree(TEMP_MEDIA_ROOT)

    # --- MotorcycleCreateView Tests ---

    def test_create_view_requires_staff_login_get(self):
        """Test that GET request to create view requires staff login."""
        response = self.client.get(self.create_url)
        # Should redirect to login page
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('users:login'), response.url) # Assuming your login URL name is 'users:login'

        # Test regular user is denied
        self.client.login(username='regularuser', password='password')
        response = self.client.get(self.create_url)
        # Should return 403 Forbidden for regular users
        self.assertEqual(response.status_code, 403)

        # Test staff user can access
        self.client.login(username='staffuser', password='password')
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/motorcycles/motorcycle_form.html')
        self.assertIn('form', response.context)
        self.assertIn('images_formset', response.context)


    def test_create_view_valid_post(self):
        """Test valid POST request to create view."""
        self.client.login(username='staffuser', password='password')

        # Mock file uploads
        # Create dummy image files
        main_image = SimpleUploadedFile("main_image.jpg", b"file_content", content_type="image/jpeg")
        additional_image_1 = SimpleUploadedFile("add_image_1.png", b"file_content_1", content_type="image/png")
        additional_image_2 = SimpleUploadedFile("add_image_2.gif", b"file_content_2", content_type="image/gif")


        form_data = {
            'brand': 'Kawasaki',
            'model': 'Z650',
            'year': 2023,
            'price': Decimal('7500.00'),
            'odometer': 0,
            'engine_size': '650cc',
            'seats': 2,
            'transmission': 'manual',
            'description': 'New naked bike.',
            'is_available': True,
            # Note: conditions is a ManyToMany field, pass a list of IDs
            'conditions': [self.new_condition.pk],
            # rego, rego_exp, stock_number, hire rates are optional
            'image': main_image, # Main image upload
            # additional_images is handled outside the formset
        }

        # Data for the image formset (initial empty forms for new images)
        # You need prefix, TOTAL_FORMS, INITIAL_FORMS, MIN_NUM_FORMS, MAX_NUM_FORMS
        formset_data = {
            'images-TOTAL_FORMS': '2',  # Indicate 2 forms in the formset (1 extra + 1 for potential existing)
            'images-INITIAL_FORMS': '0', # No initial forms (no existing images)
            'images-MIN_NUM_FORMS': '0',
            'images-MAX_NUM_FORMS': '1000', # Use a large enough number
            'images-0-image': '', # First empty form (not used for additional_images)
            'images-1-image': '', # Second empty form
            # No image fields for images-0 or images-1 here, as they are handled by additional_images input
        }

        # Combine form data and formset data
        post_data = {**form_data, **formset_data}

        # Files need to be passed separately in the 'files' argument
        files_data = {
             'image': main_image,
             'additional_images': [additional_image_1, additional_image_2], # Name of the file input in the template
        }

        # Initially, there's one motorcycle (the one for update/delete tests)
        initial_motorcycle_count = Motorcycle.objects.count()
        initial_image_count = MotorcycleImage.objects.count()

        response = self.client.post(self.create_url, data=post_data, files=files_data)

        # Should redirect on success
        self.assertEqual(response.status_code, 302)

        # Get the newly created motorcycle
        new_motorcycle = Motorcycle.objects.latest('pk') # Assumes higher PK for newer
        self.assertEqual(Motorcycle.objects.count(), initial_motorcycle_count + 1)

        # Check the created motorcycle's attributes
        self.assertEqual(new_motorcycle.brand, 'Kawasaki') # Check cleaning/capitalization if applicable
        self.assertEqual(new_motorcycle.model, 'Z650') # Check cleaning/capitalization
        self.assertEqual(new_motorcycle.year, 2023)
        self.assertEqual(new_motorcycle.price, Decimal('7500.00'))
        self.assertTrue(new_motorcycle.is_available)
        self.assertTrue(new_motorcycle.conditions.filter(name='new').exists())
        self.assertEqual(new_motorcycle.conditions.count(), 1) # Only 'new' condition

        # Check the main image was saved
        self.assertTrue(new_motorcycle.image.name.endswith('main_image.jpg')) # Check filename

        # Check the additional images were saved
        self.assertEqual(new_motorcycle.images.count(), 2)
        self.assertTrue(new_motorcycle.images.filter(image__endswith='add_image_1.png').exists())
        self.assertTrue(new_motorcycle.images.filter(image__endswith='add_image_2.gif').exists())
        self.assertEqual(MotorcycleImage.objects.count(), initial_image_count + 2) # Check total image count

        # Check redirect URL - should be the detail page of the new motorcycle
        self.assertRedirects(response, reverse('inventory:motorcycle-detail', kwargs={'pk': new_motorcycle.pk}))

        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Motorcycle added successfully!")


    def test_create_view_invalid_post(self):
        """Test invalid POST request to create view."""
        self.client.login(username='staffuser', password='password')

        # Invalid data (missing required fields like brand, model, year, seats, transmission)
        form_data = {
            'description': 'This data is incomplete.',
            'is_available': False,
            # Missing many required fields
        }

        # Formset data is still needed for the view to process it
        formset_data = {
             'images-TOTAL_FORMS': '1',
             'images-INITIAL_FORMS': '0',
             'images-MIN_NUM_FORMS': '0',
             'images-MAX_NUM_FORMS': '1000',
             'images-0-image': '',
        }
        post_data = {**form_data, **formset_data}


        initial_motorcycle_count = Motorcycle.objects.count()
        initial_image_count = MotorcycleImage.objects.count()

        response = self.client.post(self.create_url, data=post_data)

        # Should not redirect, should render the form again
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/motorcycles/motorcycle_form.html')

        # Should not create a new motorcycle or image
        self.assertEqual(Motorcycle.objects.count(), initial_motorcycle_count)
        self.assertEqual(MotorcycleImage.objects.count(), initial_image_count)

        # Check that form errors are present in the context
        form = response.context['form']
        self.assertTrue(form.errors)
        self.assertIn('brand', form.errors)
        self.assertIn('model', form.errors)
        self.assertIn('year', form.errors)
        self.assertIn('seats', form.errors)
        self.assertIn('transmission', form.errors)


    # --- MotorcycleUpdateView Tests ---

    def test_update_view_requires_staff_login_get(self):
        """Test that GET request to update view requires staff login."""
        response = self.client.get(self.update_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('users:login'), response.url)

        # Test regular user is denied
        self.client.login(username='regularuser', password='password')
        response = self.client.get(self.update_url)
        self.assertEqual(response.status_code, 403)

        # Test staff user can access
        self.client.login(username='staffuser', password='password')
        response = self.client.get(self.update_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/motorcycles/motorcycle_form.html')
        self.assertIn('form', response.context)
        self.assertIn('images_formset', response.context)
        self.assertEqual(response.context['motorcycle'], self.motorcycle_to_manage)
        # Check form is pre-populated
        self.assertEqual(response.context['form'].initial['brand'], 'Ducati')


    def test_update_view_valid_post(self):
        """Test valid POST request to update view."""
        self.client.login(username='staffuser', password='password')

        # Add an existing image to the motorcycle to test deletion/changes
        existing_image = SimpleUploadedFile("existing_image.jpg", b"existing_content", content_type="image/jpeg")
        motorcycle_image = MotorcycleImage.objects.create(
             motorcycle=self.motorcycle_to_manage,
             image=existing_image # Use SimpleUploadedFile here for realism, though it's saved to TEMP_MEDIA_ROOT
         )


        # Updated data
        form_data = {
            'brand': 'DUCATI', # Test capitalization cleaning
            'model': 'Monster 937',
            'year': 2023, # Updated year
            'price': Decimal('11500.00'), # Updated price
            'odometer': 6500,
            'engine_size': '937cc',
            'seats': 2,
            'transmission': 'manual',
            'description': 'Updated description.',
            'is_available': False, # Change availability
            # Update conditions - remove 'used', add 'new' and 'hire'
            'conditions': [self.new_condition.pk, self.hire_condition.pk],
            'rego': 'UPDATED',
            'stock_number': 'D002',
            'daily_hire_rate': Decimal('90.00'), # Add hire rate
        }

        # Data for the image formset
        # Needs to include data for the existing image and potentially empty forms for new images
        formset_data = {
            'images-TOTAL_FORMS': '2',  # 1 existing + 1 extra
            'images-INITIAL_FORMS': '1', # 1 existing
            'images-MIN_NUM_FORMS': '0',
            'images-MAX_NUM_FORMS': '1000',
            # Data for the existing image - keep it, but its file might be changed (not tested here)
            'images-0-id': motorcycle_image.pk,
            'images-0-motorcycle': self.motorcycle_to_manage.pk,
            # 'images-0-image': 'path/to/existing/image.jpg', # Django handles initial file value
            # 'images-0-DELETE': '', # Don't delete the existing image
            # Empty form for a new image (if you were adding one via formset)
            'images-1-image': '', # Empty form

        }

        # To test deleting an existing image, uncomment the DELETE field for images-0
        # formset_data['images-0-DELETE'] = 'on' # Mark existing image for deletion

        # To test adding a new image via formset, you'd fill in images-1-image
        # new_additional_image = SimpleUploadedFile("new_add_image.jpg", b"new_content", content_type="image/jpeg")
        # formset_data['images-1-image'] = new_additional_image
        # formset_data['images-TOTAL_FORMS'] = '2' # 1 existing + 1 new

        # If adding new images via the separate 'additional_images' input:
        new_additional_image = SimpleUploadedFile("new_add_image.jpg", b"new_content", content_type="image/jpeg")
        files_data = {
            'additional_images': [new_additional_image], # Name of the input in the template
        }


        post_data = {**form_data, **formset_data}


        initial_motorcycle_count = Motorcycle.objects.count()
        initial_image_count = MotorcycleImage.objects.count()


        response = self.client.post(self.update_url, data=post_data, files=files_data)

        # Should redirect on success
        self.assertEqual(response.status_code, 302)

        # Refresh the motorcycle instance from the database
        self.motorcycle_to_manage.refresh_from_db()

        # Check that no new motorcycle was created
        self.assertEqual(Motorcycle.objects.count(), initial_motorcycle_count)

        # Check updated attributes
        self.assertEqual(self.motorcycle_to_manage.brand, 'Ducati') # Should be capitalized by form clean
        self.assertEqual(self.motorcycle_to_manage.model, 'Monster 937')
        self.assertEqual(self.motorcycle_to_manage.year, 2023)
        self.assertEqual(self.motorcycle_to_manage.price, Decimal('11500.00'))
        self.assertFalse(self.motorcycle_to_manage.is_available)
        self.assertEqual(self.motorcycle_to_manage.rego, 'UPDATED') # Check cleaning/capitalization if applicable
        self.assertEqual(self.motorcycle_to_manage.stock_number, 'D002')
        self.assertEqual(self.motorcycle_to_manage.daily_hire_rate, Decimal('90.00'))

        # Check updated conditions
        self.assertTrue(self.motorcycle_to_manage.conditions.filter(name='new').exists())
        self.assertTrue(self.motorcycle_to_manage.conditions.filter(name='hire').exists())
        self.assertFalse(self.motorcycle_to_manage.conditions.filter(name='used').exists()) # Used should be removed
        self.assertEqual(self.motorcycle_to_manage.conditions.count(), 2)


        # Check image count - 1 original + 1 new additional
        # If testing deletion, this would be 1 original (deleted) + 1 new = 1 total
        self.assertEqual(self.motorcycle_to_manage.images.count(), 2)
        self.assertTrue(self.motorcycle_to_manage.images.filter(pk=motorcycle_image.pk).exists()) # Existing image should still be there
        self.assertTrue(self.motorcycle_to_manage.images.filter(image__endswith='new_add_image.jpg').exists()) # New image added
        self.assertEqual(MotorcycleImage.objects.count(), initial_image_count + 1) # Initial + new image


        # Check redirect URL - should be the detail page of the updated motorcycle
        self.assertRedirects(response, reverse('inventory:motorcycle-detail', kwargs={'pk': self.motorcycle_to_manage.pk}))

        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Motorcycle updated successfully!")


    def test_update_view_invalid_post(self):
        """Test invalid POST request to update view."""
        self.client.login(username='staffuser', password='password')

        # Invalid data (e.g., missing a required field like 'seats')
        form_data = {
            'brand': 'Ducati',
            'model': 'Monster 821',
            'year': 2020,
            'price': Decimal('10000.00'),
            'odometer': 6000,
            'engine_size': '821cc',
            # Missing 'seats'
            'transmission': 'manual',
            'description': 'A fun naked bike.',
            'is_available': True,
            'conditions': [self.used_condition.pk],
        }

        # Formset data (even if empty)
        formset_data = {
             'images-TOTAL_FORMS': '1',
             'images-INITIAL_FORMS': '0',
             'images-MIN_NUM_FORMS': '0',
             'images-MAX_NUM_FORMS': '1000',
             'images-0-image': '',
        }
        post_data = {**form_data, **formset_data}

        initial_motorcycle_count = Motorcycle.objects.count()
        initial_image_count = MotorcycleImage.objects.count()

        response = self.client.post(self.update_url, data=post_data)

        # Should not redirect, should render the form again
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/motorcycles/motorcycle_form.html')

        # No new motorcycle should be created
        self.assertEqual(Motorcycle.objects.count(), initial_motorcycle_count)
        # Existing motorcycle should not be updated
        self.motorcycle_to_manage.refresh_from_db()
        self.assertEqual(self.motorcycle_to_manage.year, 2020) # Check original value


        # Check that form errors are present in the context
        form = response.context['form']
        self.assertTrue(form.errors)
        self.assertIn('seats', form.errors)

    def test_update_view_returns_404_for_nonexistent_motorcycle(self):
        """Test that update view returns 404 for a non-existent motorcycle."""
        nonexistent_update_url = reverse('inventory:motorcycle-update', kwargs={'pk': 999})
        self.client.login(username='staffuser', password='password')
        response = self.client.get(nonexistent_update_url)
        self.assertEqual(response.status_code, 404)


    # --- MotorcycleDeleteView Tests ---

    def test_delete_view_requires_staff_login_get(self):
        """Test that GET request to delete view requires staff login."""
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('users:login'), response.url)

        # Test regular user is denied
        self.client.login(username='regularuser', password='password')
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 403)

        # Test staff user can access
        self.client.login(username='staffuser', password='password')
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/motorcycles/motorcycle_confirm_delete.html')
        self.assertIn('motorcycle', response.context)
        self.assertEqual(response.context['motorcycle'], self.motorcycle_to_manage)


    def test_delete_view_valid_post(self):
        """Test valid POST request to delete view."""
        self.client.login(username='staffuser', password='password')

        # Create a dummy image for the motorcycle to ensure it's deleted too
        image_to_delete = MotorcycleImage.objects.create(
             motorcycle=self.motorcycle_to_manage,
             image='path/to/dummy/delete_image.jpg'
         )


        initial_motorcycle_count = Motorcycle.objects.count()
        initial_image_count = MotorcycleImage.objects.count() # Includes image_to_delete

        response = self.client.post(self.delete_url)

        # Should redirect on success
        self.assertEqual(response.status_code, 302)

        # Check that the motorcycle is deleted
        self.assertEqual(Motorcycle.objects.count(), initial_motorcycle_count - 1)
        self.assertFalse(Motorcycle.objects.filter(pk=self.motorcycle_to_manage.pk).exists())

        # Check that the associated image is deleted (due to CASCADE)
        self.assertEqual(MotorcycleImage.objects.count(), initial_image_count - 1)
        self.assertFalse(MotorcycleImage.objects.filter(pk=image_to_delete.pk).exists())


        # Check redirect URL - should be the success_url
        self.assertRedirects(response, reverse('core:index')) # Assuming your core index URL is 'core:index'

        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        # The message includes the motorcycle's __str__ representation
        self.assertEqual(str(messages[0]), f"Motorcycle '{self.motorcycle_to_manage}' deleted successfully!")

    def test_delete_view_returns_404_for_nonexistent_motorcycle(self):
        """Test that delete view returns 404 for a non-existent motorcycle."""
        nonexistent_delete_url = reverse('inventory:motorcycle-delete', kwargs={'pk': 999})
        self.client.login(username='staffuser', password='password')
        response = self.client.get(nonexistent_delete_url)
        self.assertEqual(response.status_code, 404)

    def test_delete_view_invalid_post(self):
        """Test invalid POST (e.g., no data) to delete view - should still delete if allowed."""
        # DELETE views typically don't process form data in the same way as Create/Update
        # The main check is authentication and object existence.
        self.client.login(username='staffuser', password='password')

        initial_motorcycle_count = Motorcycle.objects.count()

        # Sending an empty POST request
        response = self.client.post(self.delete_url, data={})

        # Should still redirect and delete the object
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Motorcycle.objects.count(), initial_motorcycle_count - 1)
        self.assertRedirects(response, reverse('core:index'))