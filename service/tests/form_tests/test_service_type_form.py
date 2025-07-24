from django.test import TestCase
from decimal import Decimal

from service.forms import AdminServiceTypeForm
from service.models import ServiceType


from service.tests.test_helpers.model_factories import ServiceTypeFactory


class AdminServiceTypeFormTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.service_type_instance = ServiceTypeFactory(
            name="Existing Service",
            description="A pre-existing service for testing updates.",
            estimated_duration_days=2,
            base_price=Decimal("150.00"),
            is_active=True,
            slots_required=2,
        )

    def test_form_valid_data_all_fields(self):
        data = {
            "name": "Full Service Check",
            "description": "Comprehensive check-up and minor adjustments.",
            "estimated_duration_days": 1,
            "base_price": "120.50",
            "is_active": True,
            "slots_required": 1,
        }
        form = AdminServiceTypeForm(data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors.as_data()}")

        cleaned_data = form.cleaned_data
        self.assertEqual(cleaned_data["name"], "Full Service Check")
        self.assertEqual(
            cleaned_data["description"], "Comprehensive check-up and minor adjustments."
        )
        self.assertEqual(cleaned_data["estimated_duration_days"], 1)
        self.assertEqual(cleaned_data["base_price"], Decimal("120.50"))
        self.assertTrue(cleaned_data["is_active"])
        self.assertIsNone(cleaned_data.get("image"))
        self.assertEqual(cleaned_data["slots_required"], 1)

    def test_form_valid_data_duration_only_days(self):
        data = {
            "name": "Major Repair",
            "description": "Extensive engine overhaul.",
            "estimated_duration_days": 5,
            "base_price": "500.00",
            "is_active": True,
            "slots_required": 3,
        }
        form = AdminServiceTypeForm(data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors.as_data()}")
        self.assertEqual(form.cleaned_data["estimated_duration_days"], 5)

    def test_form_valid_data_zero_duration(self):
        data = {
            "name": "Consultation",
            "description": "Initial discussion with no service performed.",
            "estimated_duration_days": 0,
            "base_price": "0.00",
            "is_active": True,
            "slots_required": 1,
        }
        form = AdminServiceTypeForm(data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors.as_data()}")
        self.assertEqual(form.cleaned_data["estimated_duration_days"], 0)

    def test_form_invalid_missing_name(self):
        data = {
            "description": "Some description.",
            "estimated_duration_days": 1,
            "base_price": "100.00",
            "is_active": True,
            "slots_required": 1,
        }
        form = AdminServiceTypeForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)
        self.assertIn("This field is required.", form.errors["name"])

    def test_invalid_slots_required_negative(self):
        data = {
            "name": "Test Service Type",
            "description": "A description",
            "estimated_duration_days": 1,
            "base_price": 100.00,
            "is_active": True,
            "slots_required": -1,
        }
        form = AdminServiceTypeForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("slots_required", form.errors)

    def test_invalid_slots_required_zero(self):
        data = {
            "name": "Test Service Type",
            "description": "A description",
            "estimated_duration_days": 1,
            "base_price": 100.00,
            "is_active": True,
            "slots_required": 0,
        }
        form = AdminServiceTypeForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("slots_required", form.errors)

    def test_form_invalid_negative_base_price(self):
        data = {
            "name": "Test Service with Negative Price",
            "description": "Description",
            "estimated_duration_days": 1,
            "base_price": "-10.00",
            "is_active": True,
            "slots_required": 1,
        }
        form = AdminServiceTypeForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("base_price", form.errors)
        self.assertIn("Base price cannot be negative.", form.errors["base_price"])

    def test_form_initialization_with_instance(self):
        instance = self.service_type_instance
        form = AdminServiceTypeForm(instance=instance)

        self.assertEqual(form.initial["name"], instance.name)
        self.assertEqual(form.initial["description"], instance.description)
        self.assertEqual(
            form.initial["estimated_duration_days"], instance.estimated_duration_days
        )
        self.assertEqual(form.initial.get("estimated_duration_days_hours"), None)
        self.assertEqual(form.initial["base_price"], instance.base_price)
        self.assertEqual(form.initial["is_active"], instance.is_active)
        self.assertEqual(form.initial["slots_required"], instance.slots_required)

    def test_form_save_creates_new_instance(self):
        initial_count = ServiceType.objects.count()
        data = {
            "name": "New Service",
            "description": "A brand new service offering.",
            "estimated_duration_days": 4,
            "base_price": "75.00",
            "is_active": False,
            "slots_required": 2,
        }
        form = AdminServiceTypeForm(data=data)
        self.assertTrue(
            form.is_valid(),
            f"Form not valid for saving new instance: {form.errors.as_data()}",
        )

        new_instance = form.save()
        self.assertEqual(ServiceType.objects.count(), initial_count + 1)
        self.assertIsInstance(new_instance, ServiceType)
        self.assertEqual(new_instance.name, data["name"])
        self.assertEqual(new_instance.description, data["description"])
        self.assertEqual(new_instance.estimated_duration_days, 4)
        self.assertEqual(new_instance.base_price, Decimal("75.00"))
        self.assertFalse(new_instance.is_active)
        self.assertEqual(new_instance.slots_required, 2)

    def test_form_save_updates_existing_instance(self):
        instance = self.service_type_instance

        updated_data = {
            "name": "Updated Service Name",
            "description": "Description has been changed.",
            "estimated_duration_days": 3,
            "base_price": "200.00",
            "is_active": False,
            "slots_required": 3,
        }

        form = AdminServiceTypeForm(data=updated_data, instance=instance)
        self.assertTrue(
            form.is_valid(),
            f"Form not valid for updating instance: {form.errors.as_data()}",
        )

        updated_instance = form.save()
        self.assertEqual(updated_instance.pk, instance.pk)
        self.assertEqual(updated_instance.name, updated_data["name"])
        self.assertEqual(updated_instance.description, updated_data["description"])
        self.assertEqual(updated_instance.estimated_duration_days, 3)
        self.assertEqual(updated_instance.base_price, Decimal("200.00"))
        self.assertFalse(updated_instance.is_active)
        self.assertEqual(updated_instance.slots_required, 3)

        refreshed_instance = ServiceType.objects.get(pk=instance.pk)
        self.assertEqual(refreshed_instance.name, updated_data["name"])
        self.assertEqual(refreshed_instance.description, updated_data["description"])
        self.assertEqual(refreshed_instance.estimated_duration_days, 3)
        self.assertEqual(refreshed_instance.base_price, Decimal("200.00"))
        self.assertFalse(refreshed_instance.is_active)
        self.assertEqual(refreshed_instance.slots_required, 3)

    def test_form_image_field_optional(self):
        data_valid = {
            "name": "Service with No Image",
            "description": "This service has no icon image.",
            "estimated_duration_days": 1,
            "base_price": "50.00",
            "is_active": True,
            "slots_required": 1,
        }
        form_no_image = AdminServiceTypeForm(data=data_valid)
        self.assertTrue(
            form_no_image.is_valid(),
            f"Form is not valid with no image: {form_no_image.errors.as_data()}",
        )
        self.assertIsNone(form_no_image.cleaned_data.get("image"))

        data_empty_image = data_valid.copy()
        data_empty_image["image"] = None
        form_empty_image = AdminServiceTypeForm(data=data_empty_image)
        self.assertTrue(
            form_empty_image.is_valid(),
            f"Form is not valid with empty image data: {form_empty_image.errors.as_data()}",
        )
        self.assertIsNone(form_empty_image.cleaned_data.get("image"))
