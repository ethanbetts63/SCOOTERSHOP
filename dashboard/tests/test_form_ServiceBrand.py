from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
import io
from PIL import Image

from dashboard.forms import ServiceBrandForm
from dashboard.models import ServiceBrand


class ServiceBrandFormTest(TestCase):
    def setUp(self):
        image_file = io.BytesIO()
        Image.new('RGB', (10, 10), color = 'red').save(image_file, 'JPEG')
        image_file.seek(0)

        self.test_image = SimpleUploadedFile(
            name='test_image.jpg',
            content=image_file.read(),
            content_type='image/jpeg'
        )


    # Test form is valid with all fields properly filled.
    def test_form_valid_with_all_fields(self):
        form_data = {
            'name': 'Test Brand',
            'is_primary': True,
        }
        form_files = {
            'image': self.test_image
        }

        form = ServiceBrandForm(data=form_data, files=form_files)
        self.assertTrue(form.is_valid(), form.errors)

    # Test form is valid for non-primary brand without image.
    def test_form_valid_non_primary_without_image(self):
        form_data = {
            'name': 'Test Brand',
            'is_primary': False,
        }

        form = ServiceBrandForm(data=form_data)
        self.assertTrue(form.is_valid())

    # Test form is invalid when primary brand has no image.
    def test_form_invalid_primary_without_image(self):
        form_data = {
            'name': 'Test Brand',
            'is_primary': True,
        }

        form = ServiceBrandForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('image', form.errors)
        self.assertEqual(form.errors['image'][0], "Primary brands require an image.")

    # Test form requires name field.
    def test_form_requires_name(self):
        form_data = {
            'is_primary': False,
        }

        form = ServiceBrandForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

    # Test form initializes correctly with instance.
    def test_form_instance_initialization(self):
        brand = ServiceBrand.objects.create(
            name='Existing Brand',
            is_primary=False
        )

        form = ServiceBrandForm(instance=brand)

        self.assertEqual(form.initial['name'], 'Existing Brand')
        self.assertEqual(form.initial['is_primary'], False)

    # Test form is valid when editing an instance with an image but no new image provided.
    def test_form_valid_with_instance_no_new_image(self):
        image_file = io.BytesIO()
        Image.new('RGB', (10, 10), color = 'green').save(image_file, 'PNG')
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

        form_data = {
            'name': 'Updated Brand Name',
            'is_primary': True,
        }

        form = ServiceBrandForm(data=form_data, instance=brand_with_image)

        self.assertTrue(form.is_valid(), form.errors)


    # Test form is valid when editing an instance and providing a new image.
    def test_form_valid_with_instance_new_image(self):
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

        image_file_new = io.BytesIO()
        Image.new('RGB', (10, 10), color = 'purple').save(image_file_new, 'JPEG')
        image_file_new.seek(0)
        new_mock_image = SimpleUploadedFile(
            name='new_image.jpg',
            content=image_file_new.read(),
            content_type='image/jpeg'
        )


        form_data = {
            'name': 'Brand with New Image',
            'is_primary': True,
        }

        form_files = {
            'image': new_mock_image
        }

        form = ServiceBrandForm(data=form_data, files=form_files, instance=brand_with_image)

        self.assertTrue(form.is_valid(), form.errors)
