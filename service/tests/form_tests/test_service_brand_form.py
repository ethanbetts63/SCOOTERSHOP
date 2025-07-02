from django.test import TestCase
from service.forms import ServiceBrandForm
from ..test_helpers.model_factories import ServiceBrandFactory


class ServiceBrandFormTest(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.brand1 = ServiceBrandFactory(name="Brand A", image=None)
        cls.brand2 = ServiceBrandFactory(name="Brand B", image=None)

    def test_form_valid_data(self):

        data = {"name": "New Valid Brand"}

        form = ServiceBrandForm(data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")
        brand = form.save()
        self.assertEqual(brand.name, "New Valid Brand")
        self.assertIsNotNone(brand.pk)

        self.assertIsNone(brand.image.name if brand.image else None)

    def test_form_invalid_data_missing_name(self):

        data = {"name": ""}
        form = ServiceBrandForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)
        self.assertIn("This field is required.", form.errors["name"])

    def test_form_invalid_data_duplicate_name(self):

        data = {"name": "Brand A"}
        form = ServiceBrandForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

        self.assertIn(
            "Service Brand with this Name already exists.", form.errors["name"]
        )

    def test_form_update_existing_brand(self):

        existing_brand = self.brand1

        data = {"name": "Updated Brand A"}

        form = ServiceBrandForm(data=data, instance=existing_brand)
        self.assertTrue(
            form.is_valid(), f"Form not valid for updating brand: {form.errors}"
        )
        updated_brand = form.save()
        self.assertEqual(updated_brand.name, "Updated Brand A")
        self.assertEqual(updated_brand.pk, existing_brand.pk)

        self.assertIsNone(updated_brand.image.name if updated_brand.image else None)
