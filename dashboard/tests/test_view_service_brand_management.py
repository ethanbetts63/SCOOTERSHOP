from django.test import TestCase, Client
from django.urls import reverse
# Import get_user_model to correctly access the custom user model
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.messages import get_messages

from dashboard.models import ServiceBrand

# Import Pillow to create a fake image for testing
import io
from PIL import Image

# Get the custom user model
User = get_user_model()


class ServiceBrandManagementViewTest(TestCase):
    def setUp(self):
        # Create a staff user using the custom user model
        self.staff_user = User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='password123',
            is_staff=True
        )

        # Create a regular user using the custom user model
        self.regular_user = User.objects.create_user(
            username='regularuser',
            email='regular@example.com',
            password='password123'
        )

        # Create a test image file (using Pillow for a more realistic mock)
        image_file = io.BytesIO()
        Image.new('RGB', (10, 10), color = 'red').save(image_file, 'JPEG') # Create a small red JPEG
        image_file.seek(0) # Rewind the file pointer

        self.test_image = SimpleUploadedFile(
            name='test_image.jpg',
            content=image_file.read(), # Read the binary content
            content_type='image/jpeg'
        )

        # Create some initial service brands
        # Ensure brand1 has an image if it's primary, using the test image
        self.brand1 = ServiceBrand.objects.create(
            name='Brand One',
            is_primary=True,
            # Assign the test image to the file field for the primary brand
            # Note: In a real scenario, you might need to save the file properly
            # or adjust your model/storage for tests. Assigning the SimpleUploadedFile
            # directly might work depending on your field definition and Django version.
            # A more robust way might involve default_storage.save.
            # For this example, assigning directly to the field might suffice for tests.
            # If this still causes issues, consider using default_storage.save
            # and assigning the resulting path.
            image=self.test_image # Assign the SimpleUploadedFile instance
            # If the above doesn't work, you might need:
            # from django.core.files.storage import default_storage
            # file_name = default_storage.save('brand1.jpg', self.test_image)
            # image=file_name
        )

        self.brand2 = ServiceBrand.objects.create(
            name='Brand Two',
            is_primary=False
            # brand2 is not primary, so no image needed for initial creation based on common logic
        )

        # Set up the test client
        self.client = Client()

        # URL for the management view
        self.management_url = reverse('dashboard:service_brands_management')

    # Add tearDown to clean up created image files if necessary
    # This depends on your storage setup. If using Django's default storage
    # which saves to the filesystem, you might need to delete the files.
    # def tearDown(self):
    #     if self.brand1.image:
    #         self.brand1.image.delete(save=False)
    #     # If you created other files, delete them here


    def test_view_requires_login(self):
        """Test that view requires login."""
        response = self.client.get(self.management_url)
        # Should redirect to login page
        self.assertEqual(response.status_code, 302)
        # Check if the redirect URL contains the login path
        self.assertIn(reverse('users:login'), response.url) # Assuming 'account_login' is your login URL name


    def test_view_requires_staff_access(self):
        """Test that view requires staff status."""
        # Log in as regular user
        self.client.login(username='regularuser', password='password123')
        response = self.client.get(self.management_url)

        # Should redirect, typically to a permission denied page or login
        # Status code for redirect is 302
        self.assertEqual(response.status_code, 302)
        # The exact redirect URL depends on your settings (e.g., LOGIN_URL, LOGIN_REDIRECT_URL, etc.)
        # It might redirect back to login or to a specific denied page.
        # You might need to adjust the assertion here based on where a non-staff logged-in user is redirected.
        # Example: self.assertIn(reverse('permission_denied'), response.url)
        # Example: self.assertIn(settings.LOGIN_URL, response.url)


    def test_get_management_view_as_staff(self):
        """Test GET request for management view as staff user."""
        # Log in as staff user
        self.client.login(username='staffuser', password='password123')
        response = self.client.get(self.management_url)

        # Should return 200 OK
        self.assertEqual(response.status_code, 200)

        # Check context
        self.assertIn('form', response.context)
        self.assertIn('service_brands', response.context)
        self.assertIn('primary_brands_count', response.context)
        self.assertEqual(response.context['primary_brands_count'], 1)

        # Check template
        self.assertTemplateUsed(response, 'dashboard/service_brands_management.html')

    def test_add_brand(self):
        """Test adding a new brand."""
        # Log in as staff user
        self.client.login(username='staffuser', password='password123')

        # Prepare form data
        form_data = {
            'name': 'New Test Brand',
            'is_primary': False,
            'add_brand_submit': 'Add'
        }

        # Send POST request
        response = self.client.post(self.management_url, form_data)

        # Should redirect after successful addition
        self.assertEqual(response.status_code, 302)

        # Check brand was added
        self.assertTrue(ServiceBrand.objects.filter(name='New Test Brand').exists())

        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("added successfully" in str(msg) for msg in messages))

    def test_add_primary_brand_with_image(self):
        """Test adding a primary brand with image."""
        # Log in as staff user
        self.client.login(username='staffuser', password='password123')

        # Create a new mock image for this specific test case
        image_file = io.BytesIO()
        Image.new('RGB', (10, 10), color = 'blue').save(image_file, 'JPEG')
        image_file.seek(0)
        mock_image = SimpleUploadedFile(
            name='new_primary_image.jpg',
            content=image_file.read(),
            content_type='image/jpeg'
        )

        # Prepare form data
        form_data = {
            'name': 'New Primary Brand',
            'is_primary': True,
            'add_brand_submit': 'Add'
        }

        form_files = {
            'image': mock_image # Use the new mock image
        }

        # Send POST request with files
        response = self.client.post(self.management_url, form_data, files=form_files)

        # Should redirect after successful addition
        # The view redirects on successful form submission
        self.assertEqual(response.status_code, 302)

        # Check brand was added as primary and has an image
        try:
            new_brand = ServiceBrand.objects.get(name='New Primary Brand')
            self.assertTrue(new_brand.is_primary)
            # Check if the image field is populated
            self.assertTrue(bool(new_brand.image))
        except ServiceBrand.DoesNotExist:
            self.fail("Brand was not added.")

        # Clean up the mock image file created by this test if necessary
        # if new_brand and new_brand.image:
        #    new_brand.image.delete(save=False)


    def test_add_primary_brand_without_image_fails(self):
        """Test adding a primary brand without image fails."""
        # Log in as staff user
        self.client.login(username='staffuser', password='password123')

        # Prepare form data
        form_data = {
            'name': 'Invalid Primary Brand',
            'is_primary': True,
            'add_brand_submit': 'Add'
        }

        # Send POST request without an image file
        response = self.client.post(self.management_url, form_data)

        # Should not redirect, should render the same page with errors
        # Status code should be 200 because the form is invalid and page is re-rendered
        self.assertEqual(response.status_code, 200)

        # Check brand was NOT added
        self.assertFalse(ServiceBrand.objects.filter(name='Invalid Primary Brand').exists())

        # Check error message in the form
        self.assertIn('form', response.context)
        form = response.context['form']
        self.assertFalse(form.is_valid())
        self.assertIn('image', form.errors)
        # Optional: Check the specific error message content if known, e.g.:
        # self.assertIn("This field is required", str(form.errors['image']))


    def test_edit_brand(self):
        """Test editing an existing brand."""
        # Log in as staff user
        self.client.login(username='staffuser', password='password123')

        # Prepare the POST data for editing brand2 (which is not primary and has no initial image)
        edit_form_data = {
            'name': 'Updated Brand Name',
            'is_primary': False, # Keep as not primary
            'brand_id': self.brand2.pk,
            'add_brand_submit': 'Update' # Button name used for both add/update in view
        }

        # Send the POST request to update the brand
        # No files are included as we are not changing the image in this test
        response = self.client.post(self.management_url, edit_form_data)

        # Should redirect after successful update
        # The view redirects on successful form submission
        self.assertEqual(response.status_code, 302)

        # Check brand was updated
        self.brand2.refresh_from_db()
        self.assertEqual(self.brand2.name, 'Updated Brand Name')
        self.assertFalse(self.brand2.is_primary) # Ensure primary status didn't change unexpectedly

        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("updated successfully" in str(msg) for msg in messages))

    def test_delete_brand(self):
        """Test deleting a brand."""
        # Log in as staff user
        self.client.login(username='staffuser', password='password123')

        # Prepare delete request
        delete_data = {
            'delete_brand_pk': self.brand2.pk,
            # The view checks for 'delete_brand_pk' in POST, no specific submit button name is checked for deletion itself
            # but including one that might be present in the form is harmless.
            # 'delete_brand_submit': 'Delete' # If your form has a submit button for delete with this name
        }

        # Send POST request
        response = self.client.post(self.management_url, delete_data)

        # Should redirect after successful deletion
        # The view redirects after deleting
        self.assertEqual(response.status_code, 302)
        # Optional: Check the redirect URL is the management page
        self.assertEqual(response.url, reverse('dashboard:service_brands_management'))

        # Check brand was deleted
        self.assertFalse(ServiceBrand.objects.filter(pk=self.brand2.pk).exists())

        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("deleted successfully" in str(msg) for msg in messages))


# --- Separate Delete View Tests ---

class DeleteServiceBrandViewTest(TestCase):
    def setUp(self):
        # Create a staff user using the custom user model
        self.staff_user = User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='password123',
            is_staff=True
        )

        # Create a test brand to delete
        self.brand = ServiceBrand.objects.create(
            name='Brand To Delete',
            is_primary=False
        )

        # Set up the test client
        self.client = Client()

        # URL for the delete view
        self.delete_url = reverse('dashboard:delete_service_brand', args=[self.brand.pk])

    def test_delete_view_requires_login(self):
        """Test that delete view requires login."""
        response = self.client.post(self.delete_url)
        # Should redirect to login page
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('users:login'), response.url) # Assuming 'account_login' is your login URL name


    def test_delete_view_requires_staff_access(self):
        """Test that delete view requires staff status."""
        # Log in as regular user
        self.client.login(username='regularuser', password='password123')
        response = self.client.post(self.delete_url)

        # Should redirect for permission denied (302)
        self.assertEqual(response.status_code, 302)
        # Adjust assertion for the redirect URL based on your setup


    def test_delete_view_requires_post(self):
        """Test that delete view only accepts POST requests."""
        # Log in as staff user
        self.client.login(username='staffuser', password='password123')

        # Try GET request
        response = self.client.get(self.delete_url)

        # The view explicitly checks if method is not POST and redirects with a message
        self.assertEqual(response.status_code, 302)
        # Optional: Check the redirect URL
        self.assertEqual(response.url, reverse('dashboard:service_brands_management'))
        # Optional: Check for the specific error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Invalid request method" in str(msg) for msg in messages))

        # Confirm brand still exists
        self.assertTrue(ServiceBrand.objects.filter(pk=self.brand.pk).exists())

    def test_delete_brand_via_separate_view(self):
        """Test deleting a brand via the dedicated delete view."""
        # Log in as staff user
        self.client.login(username='staffuser', password='password123')

        # Send POST request
        response = self.client.post(self.delete_url)

        # Should redirect after successful deletion
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('dashboard:service_brands_management'))

        # Check brand was deleted
        self.assertFalse(ServiceBrand.objects.filter(pk=self.brand.pk).exists())

        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("deleted successfully" in str(msg) for msg in messages))

    def test_delete_nonexistent_brand(self):
        """Test attempting to delete a non-existent brand."""
        # Log in as staff user
        self.client.login(username='staffuser', password='password123')

        # Non-existent brand ID
        non_existent_pk = 9999
        non_existent_url = reverse('dashboard:delete_service_brand', args=[non_existent_pk])

        # Send POST request
        response = self.client.post(non_existent_url)

        # Based on the view code, get_object_or_404 raises Http404,
        # which is caught by the generic Exception handler, leading to a redirect (302).
        # Update the assertion to expect the redirect.
        self.assertEqual(response.status_code, 302)
        # Optional: Check the redirect URL
        self.assertEqual(response.url, reverse('dashboard:service_brands_management'))
        # Optional: Check for an error message (the generic exception message)
        messages = list(get_messages(response.wsgi_request))
        # The error message will be "Error deleting service brand: Http404 at /delete-url/" or similar
        self.assertTrue(any("Error deleting service brand:" in str(msg) for msg in messages))