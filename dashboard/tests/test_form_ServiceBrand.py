from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
# Import Pillow and io to create a fake image for testing
import io
from PIL import Image

from dashboard.forms import ServiceBrandForm
from dashboard.models import ServiceBrand


class ServiceBrandFormTest(TestCase):
    def setUp(self):
        # Create a test image file with valid content using Pillow
        image_file = io.BytesIO()
        # Create a very small, simple JPEG image (e.g., 10x10 red square)
        Image.new('RGB', (10, 10), color = 'red').save(image_file, 'JPEG')
        image_file.seek(0) # Rewind the file pointer to the beginning

        self.test_image = SimpleUploadedFile(
            name='test_image.jpg',
            content=image_file.read(),  # Read the binary content from the BytesIO object
            content_type='image/jpeg'
        )

        # You might also need to create a ServiceBrand instance with an image
        # if any of your tests involve updating an existing instance with or without
        # providing a new image. However, based on the failures, the current tests
        # don't seem to strictly require this for the initial fix.

    # Add tearDown to clean up created image files if your storage backend
    # saves them to the file system during tests.
    # def tearDown(self):
    #     # Example cleanup if a brand instance with an image was created and saved
    #     try:
    #         brand_with_image = ServiceBrand.objects.get(name='Brand with Image')
    #         if brand_with_image.image:
    #              brand_with_image.image.delete(save=False)
    #     except ServiceBrand.DoesNotExist:
    #         pass


    def test_form_valid_with_all_fields(self):
        """Test form is valid with all fields properly filled."""
        form_data = {
            'name': 'Test Brand',
            'is_primary': True,
        }
        form_files = {
            'image': self.test_image # This now contains valid image content
        }

        form = ServiceBrandForm(data=form_data, files=form_files)
        # With valid image content, the form's basic ImageField validation
        # should pass, and your clean method will also find an image, making the form valid.
        self.assertTrue(form.is_valid(), form.errors) # Print errors if invalid

    def test_form_valid_non_primary_without_image(self):
        """Test form is valid for non-primary brand without image."""
        form_data = {
            'name': 'Test Brand',
            'is_primary': False,
        }

        # No files are passed, which is correct for testing no image upload
        form = ServiceBrandForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_invalid_primary_without_image(self):
        """Test form is invalid when primary brand has no image."""
        form_data = {
            'name': 'Test Brand',
            'is_primary': True,
        }

        # No files are passed, testing the clean method's 'primary requires image' rule
        form = ServiceBrandForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('image', form.errors)
        self.assertEqual(form.errors['image'][0], "Primary brands require an image.")

    def test_form_requires_name(self):
        """Test form requires name field."""
        form_data = {
            'is_primary': False,
            # Name is missing
        }

        form = ServiceBrandForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
        # Optional: Check the specific required field error message
        # self.assertEqual(form.errors['name'][0], "This field is required.")

    def test_form_instance_initialization(self):
        """Test form initializes correctly with instance."""
        # Create a brand first
        brand = ServiceBrand.objects.create(
            name='Existing Brand',
            is_primary=False
        )

        # Initialize form with the instance
        form = ServiceBrandForm(instance=brand)

        # Check initial values
        self.assertEqual(form.initial['name'], 'Existing Brand')
        self.assertEqual(form.initial['is_primary'], False)
        # Check that the image field is represented correctly (e.g., shows existing file widget)
        # The exact assertion depends on the form field's representation. Checking if 'image' is in initial is not reliable for file fields.
        # You could check the form's rendered output if needed, but for basic instance loading, this is usually sufficient.

    def test_form_valid_with_instance_no_new_image(self):
        """Test form is valid when editing an instance with an image but no new image provided."""
        # Create a brand with an image (simulating an existing primary brand)
        image_file = io.BytesIO()
        Image.new('RGB', (10, 10), color = 'green').save(image_file, 'PNG') # Use PNG for variety
        image_file.seek(0)
        brand_with_image = ServiceBrand.objects.create(
            name='Brand with Image',
            is_primary=True,
            image=SimpleUploadedFile(
                name='existing_image.png',
                content=image_file.read(),
                content_type='image/png'
            )
        )

        # Data for editing (e.g., changing the name, keeping primary status)
        form_data = {
            'name': 'Updated Brand Name',
            'is_primary': True, # Keep as primary
            # No 'image' key in form_data or form_files
        }

        # Initialize form with the instance and process the POST data
        # When data=... and files=... are passed with an instance, Django attempts
        # to update the instance. If no new file is in files, it should retain the existing one.
        form = ServiceBrandForm(data=form_data, instance=brand_with_image)

        # The form should be valid because 'is_primary' is True, and there is an existing
        # image on the instance that the form should recognize and retain.
        self.assertTrue(form.is_valid(), form.errors) # Print errors if invalid

        # Optional: Save the form and verify the image field is still populated
        # updated_brand = form.save()
        # self.assertTrue(bool(updated_brand.image))
        # self.assertEqual(updated_brand.image.name, 'existing_image.png') # Or similar check

        # Clean up the created brand and its image if necessary
        # brand_with_image.delete() # This should also delete the file by default depending on storage


    def test_form_valid_with_instance_new_image(self):
        """Test form is valid when editing an instance and providing a new image."""
        # Create a brand with an existing image
        image_file_old = io.BytesIO()
        Image.new('RGB', (10, 10), color = 'orange').save(image_file_old, 'GIF')
        image_file_old.seek(0)
        brand_with_image = ServiceBrand.objects.create(
            name='Brand with Old Image',
            is_primary=True,
            image=SimpleUploadedFile(
                name='old_image.gif',
                content=image_file_old.read(),
                content_type='image/gif'
            )
        )

        # Create a new mock image for the update
        image_file_new = io.BytesIO()
        Image.new('RGB', (10, 10), color = 'purple').save(image_file_new, 'JPEG')
        image_file_new.seek(0)
        new_mock_image = SimpleUploadedFile(
            name='new_image.jpg',
            content=image_file_new.read(),
            content_type='image/jpeg'
        )


        # Data for editing
        form_data = {
            'name': 'Brand with New Image',
            'is_primary': True,
            # No image in form_data, it comes via files
        }

        form_files = {
            'image': new_mock_image # Provide the new image file
        }

        # Initialize form with the instance and process the POST data and files
        form = ServiceBrandForm(data=form_data, files=form_files, instance=brand_with_image)

        # The form should be valid
        self.assertTrue(form.is_valid(), form.errors) # Print errors if invalid

        # Optional: Save the form and verify the image field is updated
        # updated_brand = form.save()
        # self.assertTrue(bool(updated_brand.image))
        # self.assertEqual(updated_brand.image.name, 'new_image.jpg') # Or similar check

        # Clean up the created brand and its image if necessary
        # brand_with_image.delete() # This should also delete the file