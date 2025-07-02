from django.test import TestCase
from django import forms
from inventory.forms.admin_motorcycle_image_form import MotorcycleImageForm
from django.core.files.uploadedfile import SimpleUploadedFile


class MotorcycleImageFormTest(TestCase):

    def test_form_fields_and_widgets(self):
        form = MotorcycleImageForm()
        expected_fields = ["image"]
        self.assertEqual(list(form.fields.keys()), expected_fields)
        self.assertIsInstance(form.fields["image"].widget, forms.FileInput)

    def test_form_with_valid_image_data(self):
        image_content = b"fake_image_data"
        image_file = SimpleUploadedFile(
            "test_image.jpg", image_content, content_type="image/jpeg"
        )
        data = {"image": image_file}
        form = MotorcycleImageForm(files=data)
        self.assertTrue(form.is_valid(), str(form.errors))
        motorcycle_image = form.save(commit=False)
        self.assertEqual(motorcycle_image.image.read(), image_content)

    def test_form_without_image_data(self):
        form = MotorcycleImageForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn("image", form.errors)
        self.assertEqual(form.errors["image"], ["This field is required."])
