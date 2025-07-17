from django.test import TestCase
from django.contrib.auth import get_user_model


from service.forms import AdminServiceProfileForm


from users.tests.test_helpers.model_factories import UserFactory
from service.tests.test_helpers.model_factories import ServiceProfileFactory

User = get_user_model()


class AdminServiceProfileFormTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unlinked_user = UserFactory(
            username="unlinked_user", email="unlinked@example.com"
        )

        cls.linked_user_existing_profile = ServiceProfileFactory().user

        cls.existing_service_profile = ServiceProfileFactory(
            name="Existing Profile",
            email="existing@example.com",
            phone_number="111222333",
            user=UserFactory(
                username="existing_profile_user", email="existing_profile@example.com"
            ),
        )
        cls.existing_service_profile_user = cls.existing_service_profile.user

    def test_form_valid_data_with_new_user_link(self):
        data = {
            "user": self.unlinked_user.pk,
            "name": "Test User Name",
            "email": "test@example.com",
            "phone_number": "1234567890",
            "address_line_1": "123 Main St",
            "city": "Anytown",
            "state": "AS",
            "post_code": "12345",
            "country": "US",
        }
        form = AdminServiceProfileForm(data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")
        self.assertEqual(form.cleaned_data["user"], self.unlinked_user)
        self.assertEqual(form.cleaned_data["name"], data["name"])
        self.assertEqual(form.cleaned_data["email"], data["email"])
        self.assertEqual(form.cleaned_data["phone_number"], data["phone_number"])

    def test_form_valid_data_without_user_link(self):
        data = {
            "user": "",
            "name": "Standalone Profile Name",
            "email": "standalone@example.com",
            "phone_number": "0987654321",
            "address_line_1": "456 Oak Ave",
            "city": "Otherville",
            "state": "OT",
            "post_code": "54321",
            "country": "CA",
        }
        form = AdminServiceProfileForm(data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")
        self.assertIsNone(form.cleaned_data["user"])
        self.assertEqual(form.cleaned_data["name"], data["name"])

    def test_form_invalid_data_missing_contact_details_without_user(self):
        data_missing_name = {
            "user": "",
            "email": "missingname@example.com",
            "phone_number": "1231231234",
            "address_line_1": "1 Testing St",
            "city": "Test",
            "state": "TS",
            "post_code": "11111",
            "country": "AU",
        }
        form = AdminServiceProfileForm(data=data_missing_name)
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)
        self.assertIn(
            "Full Name is required if no user account is linked.", form.errors["name"]
        )

        data_missing_email = {
            "user": "",
            "name": "Name Present",
            "phone_number": "1231231234",
            "address_line_1": "1 Testing St",
            "city": "Test",
            "state": "TS",
            "post_code": "11111",
            "country": "AU",
        }
        form = AdminServiceProfileForm(data=data_missing_email)
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)
        self.assertIn(
            "Email Address is required if no user account is linked.",
            form.errors["email"],
        )

        data_missing_phone = {
            "user": "",
            "name": "Name Present",
            "email": "emailpresent@example.com",
            "address_line_1": "1 Testing St",
            "city": "Test",
            "state": "TS",
            "post_code": "11111",
            "country": "AU",
        }
        form = AdminServiceProfileForm(data=data_missing_phone)
        self.assertFalse(form.is_valid())
        self.assertIn("phone_number", form.errors)
        self.assertIn(
            "Phone Number is required if no user account is linked.",
            form.errors["phone_number"],
        )

    def test_clean_user_prevents_linking_already_linked_user_to_new_profile(self):
        data = {
            "user": self.linked_user_existing_profile.pk,
            "name": "New Profile Name",
            "email": "newprofile@example.com",
            "phone_number": "9998887777",
            "address_line_1": "789 Pine St",
            "city": "Villagetown",
            "state": "VT",
            "post_code": "98765",
            "country": "NZ",
        }
        form = AdminServiceProfileForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("user", form.errors)
        self.assertIn(
            f"This user ({self.linked_user_existing_profile.username}) is already linked to another Service Profile.",
            form.errors["user"],
        )

    def test_clean_user_allows_re_linking_same_user_to_same_profile_on_update(self):
        data = {
            "user": self.existing_service_profile_user.pk,
            "name": "Updated Profile Name",
            "email": "updated@example.com",
            "phone_number": "111222333",
            "address_line_1": "123 Main St",
            "city": "Anytown",
            "state": "AS",
            "post_code": "12345",
            "country": "US",
        }

        form = AdminServiceProfileForm(
            data=data, instance=self.existing_service_profile
        )
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")

        self.assertEqual(form.cleaned_data["user"], self.existing_service_profile_user)

        self.assertEqual(form.cleaned_data["name"], "Updated Profile Name")

    def test_initial_data_for_existing_instance(self):
        form = AdminServiceProfileForm(instance=self.existing_service_profile)
        self.assertEqual(form.initial["user"], self.existing_service_profile.user.pk)
        self.assertEqual(form.initial["name"], self.existing_service_profile.name)
        self.assertEqual(form.initial["email"], self.existing_service_profile.email)
        self.assertEqual(
            form.initial["phone_number"], self.existing_service_profile.phone_number
        )

        self.assertEqual(form.initial["city"], self.existing_service_profile.city)

    def test_user_field_queryset(self):
        form = AdminServiceProfileForm()
        queryset = form.fields["user"].queryset

        self.assertIn(self.unlinked_user, queryset)
        self.assertIn(self.linked_user_existing_profile, queryset)
        self.assertIn(self.existing_service_profile_user, queryset)

        all_users = list(User.objects.all().order_by("username"))
        retrieved_users = list(queryset)
        self.assertEqual(retrieved_users, all_users)
