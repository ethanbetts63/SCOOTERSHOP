from django.test import TestCase
from service.forms import ServiceBookingUserForm


from service.tests.test_helpers.model_factories import ServiceProfileFactory


class ServiceBookingUserFormTest(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.valid_service_profile_data = {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "phone_number": "+61412345678",
            "address_line_1": "123 Main St",
            "address_line_2": "",
            "city": "Sydney",
            "state": "",
            "post_code": "2000",
            "country": "AU",
        }

    def test_form_valid_data(self):

        form = ServiceBookingUserForm(data=self.valid_service_profile_data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")

        cleaned_data = form.cleaned_data
        self.assertEqual(cleaned_data["name"], "John Doe")
        self.assertEqual(cleaned_data["email"], "john.doe@example.com")
        self.assertEqual(cleaned_data["phone_number"], "+61412345678")
        self.assertEqual(cleaned_data["address_line_1"], "123 Main St")

        self.assertIsNone(cleaned_data["address_line_2"])
        self.assertEqual(cleaned_data["city"], "Sydney")

        self.assertIsNone(cleaned_data["state"])
        self.assertEqual(cleaned_data["post_code"], "2000")
        self.assertEqual(cleaned_data["country"], "AU")

    def test_form_invalid_data_missing_required_fields(self):

        required_fields = [
            "name",
            "email",
            "phone_number",
            "address_line_1",
            "city",
            "post_code",
            "country",
        ]

        for field in required_fields:
            with self.subTest(f"Missing field: {field}"):
                data = self.valid_service_profile_data.copy()
                data[field] = ""
                form = ServiceBookingUserForm(data=data)
                self.assertFalse(form.is_valid())
                self.assertIn(field, form.errors)
                self.assertIn("This field is required.", form.errors[field])

    def test_form_invalid_email_format(self):

        data = self.valid_service_profile_data.copy()
        data["email"] = "invalid-email"
        form = ServiceBookingUserForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)
        self.assertIn("Enter a valid email address.", form.errors["email"])

        data["email"] = "user@.com"
        form = ServiceBookingUserForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)
        self.assertIn("Enter a valid email address.", form.errors["email"])

    def test_form_invalid_phone_number_format(self):

        data = self.valid_service_profile_data.copy()

        expected_error_message = "Phone number must contain only digits, spaces, hyphens, and an optional leading '+'. Example: '+61412345678' or '0412 345 678'."

        data["phone_number"] = "abc1234567"
        form = ServiceBookingUserForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("phone_number", form.errors)
        self.assertIn(expected_error_message, form.errors["phone_number"])

        data["phone_number"] = "0412!345678"
        form = ServiceBookingUserForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("phone_number", form.errors)
        self.assertIn(expected_error_message, form.errors["phone_number"])

        data["phone_number"] = "0412 345-678"
        form = ServiceBookingUserForm(data=data)
        self.assertTrue(
            form.is_valid(), f"Form is not valid with valid phone: {form.errors}"
        )
        self.assertEqual(form.cleaned_data["phone_number"], "0412 345-678")

    def test_form_with_existing_service_profile(self):

        existing_profile = ServiceProfileFactory(
            name="Jane Doe",
            email="jane.doe@example.com",
            phone_number="+61498765432",
            address_line_1="456 Oak Ave",
            address_line_2="Suite 100",
            city="Melbourne",
            state="VIC",
            post_code="3000",
            country="AU",
        )

        updated_data = {
            "name": "Jane D. Smith",
            "email": "jane.d.smith@example.com",
            "phone_number": "+61400111222",
            "address_line_1": "789 Pine Rd",
            "address_line_2": "Apt 101",
            "city": "Brisbane",
            "state": "QLD",
            "post_code": "4000",
            "country": "AU",
        }

        form = ServiceBookingUserForm(data=updated_data, instance=existing_profile)
        self.assertTrue(
            form.is_valid(), f"Form is not valid when updating instance: {form.errors}"
        )

        updated_profile = form.save()
        self.assertEqual(updated_profile.name, "Jane D. Smith")
        self.assertEqual(updated_profile.email, "jane.d.smith@example.com")
        self.assertEqual(updated_profile.phone_number, "+61400111222")
        self.assertEqual(updated_profile.address_line_1, "789 Pine Rd")
        self.assertEqual(updated_profile.address_line_2, "Apt 101")
        self.assertEqual(updated_profile.city, "Brisbane")
        self.assertEqual(updated_profile.state, "QLD")
        self.assertEqual(updated_profile.post_code, "4000")
        self.assertEqual(updated_profile.country, "AU")
        self.assertEqual(updated_profile.pk, existing_profile.pk)

    def test_form_optional_fields(self):

        data = self.valid_service_profile_data.copy()
        data["address_line_2"] = ""
        data["state"] = ""
        form = ServiceBookingUserForm(data=data)
        self.assertTrue(
            form.is_valid(),
            f"Form is not valid with empty optional fields: {form.errors}",
        )

        self.assertIsNone(form.cleaned_data["address_line_2"])
        self.assertIsNone(form.cleaned_data["state"])
