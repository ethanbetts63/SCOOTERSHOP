from django.test import TestCase
from datetime import date


from service.forms import AdminCustomerMotorcycleForm
from service.models import CustomerMotorcycle


from ..test_helpers.model_factories import (
    ServiceProfileFactory,
    CustomerMotorcycleFactory,
)


class AdminCustomerMotorcycleFormTest(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.service_profile = ServiceProfileFactory(name="Test Service Profile")
        cls.valid_motorcycle_data = {
            "brand": "Honda",
            "model": "CBR1000RR",
            "year": date.today().year - 5,
            "rego": "ABC123",
            "odometer": 15000,
            "transmission": "MANUAL",
            "engine_size": "1000cc",
            "vin_number": "1234567890ABCDEFG",
            "engine_number": "ENG12345",
            "service_profile": cls.service_profile.pk,
        }

    def test_form_valid_data_create(self):

        data = self.valid_motorcycle_data.copy()
        form = AdminCustomerMotorcycleForm(data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors.as_json()}")

        motorcycle = form.save()
        self.assertIsInstance(motorcycle, CustomerMotorcycle)
        self.assertEqual(motorcycle.brand, data["brand"])
        self.assertEqual(motorcycle.service_profile, self.service_profile)

    def test_form_valid_data_create_without_service_profile(self):

        data = self.valid_motorcycle_data.copy()
        data["service_profile"] = ""
        form = AdminCustomerMotorcycleForm(data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors.as_json()}")

        motorcycle = form.save()
        self.assertIsNone(motorcycle.service_profile)

    def test_form_valid_data_update(self):

        existing_motorcycle = CustomerMotorcycleFactory(
            service_profile=self.service_profile
        )

        data = self.valid_motorcycle_data.copy()
        data["brand"] = "Yamaha"
        form = AdminCustomerMotorcycleForm(data=data, instance=existing_motorcycle)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors.as_json()}")

        motorcycle = form.save()
        self.assertEqual(motorcycle.pk, existing_motorcycle.pk)
        self.assertEqual(motorcycle.brand, "Yamaha")

    def test_missing_required_fields(self):

        required_fields = [
            "brand",
            "model",
            "year",
            "rego",
            "odometer",
            "transmission",
            "engine_size",
        ]

        for field in required_fields:
            with self.subTest(field=field):
                invalid_data = self.valid_motorcycle_data.copy()
                if field == "odometer":
                    invalid_data[field] = None
                else:
                    invalid_data[field] = ""

                form = AdminCustomerMotorcycleForm(data=invalid_data)
                self.assertFalse(form.is_valid())
                self.assertIn(field, form.errors)

                if field == "rego":
                    expected_error_message = "Motorcycle registration is required."
                elif field == "odometer":
                    expected_error_message = "Motorcycle odometer is required."
                elif field == "transmission":
                    expected_error_message = "Motorcycle transmission type is required."
                elif field == "year":
                    expected_error_message = "Motorcycle year is required."
                else:
                    expected_error_message = (
                        f"Motorcycle {field.replace('_', ' ')} is required."
                    )

                self.assertIn(expected_error_message, form.errors[field])

    def test_motorcycle_year_validation(self):

        current_year = date.today().year

        data_future_year = self.valid_motorcycle_data.copy()
        data_future_year["year"] = current_year + 1
        form = AdminCustomerMotorcycleForm(data=data_future_year)
        self.assertFalse(form.is_valid())
        self.assertIn("year", form.errors)
        self.assertIn("Motorcycle year cannot be in the future.", form.errors["year"])

        data_old_year = self.valid_motorcycle_data.copy()
        data_old_year["year"] = current_year - 101
        form = AdminCustomerMotorcycleForm(data=data_old_year)
        self.assertFalse(form.is_valid())
        self.assertIn("year", form.errors)
        self.assertIn(
            "Motorcycle year seems too old. Please check the year.", form.errors["year"]
        )

        data_zero_year = self.valid_motorcycle_data.copy()
        data_zero_year["year"] = 0
        form = AdminCustomerMotorcycleForm(data=data_zero_year)
        self.assertFalse(form.is_valid())
        self.assertIn("year", form.errors)
        self.assertIn("Motorcycle year is required.", form.errors["year"])

        data_below_widget_min = self.valid_motorcycle_data.copy()
        data_below_widget_min["year"] = 1899
        form = AdminCustomerMotorcycleForm(data=data_below_widget_min)
        self.assertFalse(form.is_valid())
        self.assertIn("year", form.errors)

        self.assertIn(
            "Motorcycle year seems too old. Please check the year.", form.errors["year"]
        )

    def test_vin_number_length_validation(self):

        data_short_vin = self.valid_motorcycle_data.copy()
        data_short_vin["vin_number"] = "SHORTVIN"
        form = AdminCustomerMotorcycleForm(data=data_short_vin)
        self.assertFalse(form.is_valid())
        self.assertIn("vin_number", form.errors)
        self.assertIn(
            "VIN number must be 17 characters long.", form.errors["vin_number"]
        )

        data_long_vin = self.valid_motorcycle_data.copy()
        data_long_vin["vin_number"] = "TOOLONGVINNUMBERXXY"
        form = AdminCustomerMotorcycleForm(data=data_long_vin)
        self.assertFalse(form.is_valid())
        self.assertIn("vin_number", form.errors)

        self.assertIn(
            "Ensure this value has at most 17 characters (it has 19).",
            form.errors["vin_number"],
        )

        data_correct_vin = self.valid_motorcycle_data.copy()
        data_correct_vin["vin_number"] = "THISISAVALIDVIN17"
        form = AdminCustomerMotorcycleForm(data=data_correct_vin)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors.as_json()}")

        data_empty_vin = self.valid_motorcycle_data.copy()
        data_empty_vin["vin_number"] = ""
        form = AdminCustomerMotorcycleForm(data=data_empty_vin)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors.as_json()}")

    def test_odometer_negative_validation(self):

        data_negative_odometer = self.valid_motorcycle_data.copy()
        data_negative_odometer["odometer"] = -100
        form = AdminCustomerMotorcycleForm(data=data_negative_odometer)
        self.assertFalse(form.is_valid())
        self.assertIn("odometer", form.errors)

        self.assertIn(
            "Ensure this value is greater than or equal to 0.", form.errors["odometer"]
        )

    def test_transmission_choices(self):

        data_invalid_transmission = self.valid_motorcycle_data.copy()
        data_invalid_transmission["transmission"] = "INVALID_TYPE"
        form = AdminCustomerMotorcycleForm(data=data_invalid_transmission)
        self.assertFalse(form.is_valid())
        self.assertIn("transmission", form.errors)
        self.assertIn(
            "Select a valid choice. INVALID_TYPE is not one of the available choices.",
            form.errors["transmission"],
        )

    def test_service_profile_queryset(self):

        profile_a = ServiceProfileFactory(name="Profile A", email="a@example.com")
        profile_b = ServiceProfileFactory(name="Profile B", email="b@example.com")
        profile_c = ServiceProfileFactory(name="Profile C", email="c@example.com")

        form = AdminCustomerMotorcycleForm()

        queryset = list(form.fields["service_profile"].queryset)

        all_profiles = [self.service_profile, profile_a, profile_b, profile_c]

        expected_order = sorted(all_profiles, key=lambda p: (p.name, p.email))

        self.assertListEqual(queryset, expected_order)
