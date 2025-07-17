from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest import mock
import tempfile
from PIL import Image
from inventory.models import SalesProfile, InventorySettings


from users.tests.test_helpers.model_factories import UserFactory
from inventory.tests.test_helpers.model_factories import (
    TempSalesBookingFactory,
    SalesProfileFactory,
    MotorcycleFactory,
    InventorySettingsFactory,
)


class Step1SalesProfileViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.url = reverse("inventory:step1_sales_profile")

        cls.inventory_settings = InventorySettingsFactory(
            require_drivers_license=False,
            require_address_info=False,
        )

        cls.motorcycle = MotorcycleFactory()

        cls.user = UserFactory(username="testuser", email="test@example.com")
        cls.user.set_password("password123")
        cls.user.save()

    def _create_temp_booking_in_session(self, client, user=None, sales_profile=None):
        temp_booking = TempSalesBookingFactory(
            motorcycle=self.motorcycle,
            sales_profile=sales_profile,
            booking_status="pending_details",
        )
        session = client.session

        session["temp_sales_booking_uuid"] = str(temp_booking.session_uuid)
        session.save()
        return temp_booking

    def _create_dummy_image(
        self, name="test_image.jpg", size=(50, 50), color=(255, 0, 0)
    ):
        file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        img = Image.new("RGB", size, color)
        img.save(file, "jpeg")
        file.close()
        return SimpleUploadedFile(
            name, open(file.name, "rb").read(), content_type="image/jpeg"
        )

    def test_get_no_temp_booking_id_in_session(self):
        response = self.client.get(self.url, follow=True)
        self.assertRedirects(response, reverse("inventory:all"))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]),
            "Your booking session has expired or is invalid. Please start again.",
        )

    def test_get_invalid_temp_booking_id(self):
        session = self.client.session
        session["temp_sales_booking_uuid"] = "a2b3c4d5-e6f7-8901-2345-67890abcdef0"
        session.save()

        response = self.client.get(self.url, follow=True)
        self.assertRedirects(response, reverse("inventory:all"))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn(
            "Your booking session could not be found or is invalid.", str(messages[0])
        )

    def test_get_no_inventory_settings(self):
        self._create_temp_booking_in_session(self.client)

        InventorySettings.objects.all().delete()
        self.assertFalse(InventorySettings.objects.exists())

        response = self.client.get(self.url, follow=True)
        self.assertRedirects(response, reverse("inventory:all"))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]),
            "Inventory settings are not configured. Please contact support.",
        )

        self.inventory_settings = InventorySettingsFactory(pk=1)

    def test_get_success_unauthenticated_user(self):
        temp_booking = self._create_temp_booking_in_session(self.client)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "inventory/step1_sales_profile.html")
        self.assertIn("sales_profile_form", response.context)
        self.assertIn("temp_booking", response.context)
        self.assertEqual(
            response.context["temp_booking"].session_uuid, temp_booking.session_uuid
        )
        self.assertIsNone(response.context["sales_profile_form"].instance.pk)

    def test_get_success_authenticated_user_no_profile(self):
        self.client.login(username="testuser", password="password123")
        temp_booking = self._create_temp_booking_in_session(self.client, user=self.user)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("sales_profile_form", response.context)
        self.assertIsNone(response.context["sales_profile_form"].instance.pk)

    def test_get_success_authenticated_user_with_profile(self):
        self.client.login(username="testuser", password="password123")
        existing_profile = SalesProfileFactory(
            user=self.user, name="Existing Name", email="existing@example.com"
        )
        temp_booking = self._create_temp_booking_in_session(self.client, user=self.user)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("sales_profile_form", response.context)
        self.assertEqual(
            response.context["sales_profile_form"].instance, existing_profile
        )

        self.assertEqual(
            response.context["sales_profile_form"]["name"].value(), "Existing Name"
        )
        self.assertEqual(
            response.context["sales_profile_form"]["email"].value(),
            "existing@example.com",
        )

    def test_get_success_temp_booking_has_profile(self):
        existing_profile_for_temp = SalesProfileFactory(
            name="Temp Linked Name", email="temp_linked@example.com"
        )
        temp_booking = self._create_temp_booking_in_session(
            self.client, sales_profile=existing_profile_for_temp
        )

        another_user = UserFactory(username="anotheruser", email="another@example.com")
        another_user.set_password("password123")
        another_user.save()
        SalesProfileFactory(
            user=another_user,
            name="Another User Profile",
            email="anotheruser@example.com",
        )
        self.client.login(username="anotheruser", password="password123")

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("sales_profile_form", response.context)

        self.assertEqual(
            response.context["sales_profile_form"].instance, existing_profile_for_temp
        )

        self.assertEqual(
            response.context["sales_profile_form"]["name"].value(), "Temp Linked Name"
        )
        self.assertEqual(
            response.context["sales_profile_form"]["email"].value(),
            "temp_linked@example.com",
        )

    @mock.patch("django.contrib.messages.success")
    @mock.patch("django.contrib.messages.error")
    def test_post_no_temp_booking_id_in_session(self, mock_error, mock_success):
        response = self.client.post(self.url, data={}, follow=True)
        self.assertRedirects(response, reverse("inventory:all"))
        mock_error.assert_called_once_with(
            mock.ANY,
            "Your booking session has expired or is invalid. Please start again.",
        )
        mock_success.assert_not_called()

    @mock.patch("django.contrib.messages.success")
    @mock.patch("django.contrib.messages.error")
    def test_post_invalid_temp_booking_id(self, mock_error, mock_success):
        session = self.client.session
        session["temp_sales_booking_uuid"] = "a2b3c4d5-e6f7-8901-2345-67890abcdef0"
        session.save()

        response = self.client.post(self.url, data={"name": "Test User"}, follow=True)
        self.assertRedirects(response, reverse("inventory:all"))
        mock_error.assert_called_once()
        self.assertIn(
            "Your booking session could not be found or is invalid.",
            str(mock_error.call_args[0][1]),
        )
        mock_success.assert_not_called()

    @mock.patch("django.contrib.messages.success")
    @mock.patch("django.contrib.messages.error")
    def test_post_no_inventory_settings(self, mock_error, mock_success):
        self._create_temp_booking_in_session(self.client)
        InventorySettings.objects.all().delete()

        response = self.client.post(self.url, data={"name": "Test User"}, follow=True)
        self.assertRedirects(response, reverse("inventory:all"))
        mock_error.assert_called_once_with(
            mock.ANY, "Inventory settings are not configured. Please contact support."
        )
        mock_success.assert_not_called()

        self.inventory_settings = InventorySettingsFactory(pk=1)

    @mock.patch("django.contrib.messages.success")
    @mock.patch("django.contrib.messages.error")
    def test_post_valid_data_new_profile_unauthenticated(
        self, mock_error, mock_success
    ):
        temp_booking = self._create_temp_booking_in_session(self.client)
        initial_profile_count = SalesProfile.objects.count()

        post_data = {
            "name": "New Customer",
            "email": "new@example.com",
            "phone_number": "0412345678",
            "date_of_birth": "1990-01-01",
        }
        response = self.client.post(self.url, data=post_data, follow=True)

        self.assertRedirects(
            response, reverse("inventory:step2_booking_details_and_appointment")
        )
        mock_success.assert_called_once_with(
            mock.ANY,
            "Personal details saved. Proceed to booking details and appointment.",
        )
        mock_error.assert_not_called()

        self.assertEqual(SalesProfile.objects.count(), initial_profile_count + 1)
        new_profile = SalesProfile.objects.latest("created_at")
        self.assertEqual(new_profile.name, "New Customer")
        self.assertEqual(new_profile.email, "new@example.com")
        self.assertIsNone(new_profile.user)

        temp_booking.refresh_from_db()
        self.assertEqual(temp_booking.sales_profile, new_profile)

    @mock.patch("django.contrib.messages.success")
    @mock.patch("django.contrib.messages.error")
    def test_post_valid_data_update_existing_profile_authenticated(
        self, mock_error, mock_success
    ):
        self.client.login(username="testuser", password="password123")
        existing_profile = SalesProfileFactory(
            user=self.user, name="Old Name", email="old@example.com", phone_number="111"
        )
        temp_booking = self._create_temp_booking_in_session(
            self.client, user=self.user, sales_profile=existing_profile
        )
        initial_profile_count = SalesProfile.objects.count()

        post_data = {
            "name": "Updated Name",
            "email": "updated@example.com",
            "phone_number": "0498765432",
            "date_of_birth": "1985-05-05",
        }
        response = self.client.post(self.url, data=post_data, follow=True)

        self.assertRedirects(
            response, reverse("inventory:step2_booking_details_and_appointment")
        )
        mock_success.assert_called_once_with(
            mock.ANY,
            "Personal details saved. Proceed to booking details and appointment.",
        )
        mock_error.assert_not_called()

        self.assertEqual(SalesProfile.objects.count(), initial_profile_count)
        existing_profile.refresh_from_db()
        self.assertEqual(existing_profile.name, "Updated Name")
        self.assertEqual(existing_profile.email, "updated@example.com")
        self.assertEqual(existing_profile.user, self.user)

        temp_booking.refresh_from_db()
        self.assertEqual(temp_booking.sales_profile, existing_profile)

    @mock.patch("django.contrib.messages.success")
    @mock.patch("django.contrib.messages.error")
    def test_post_invalid_data(self, mock_error, mock_success):
        temp_booking = self._create_temp_booking_in_session(self.client)
        initial_profile_count = SalesProfile.objects.count()

        post_data = {
            "name": "",
            "email": "invalid-email",
            "phone_number": "0412345678",
            "date_of_birth": "1990-01-01",
        }
        response = self.client.post(self.url, data=post_data)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "inventory/step1_sales_profile.html")
        mock_error.assert_called_once_with(mock.ANY, "Please correct the errors below.")
        mock_success.assert_not_called()

        self.assertEqual(SalesProfile.objects.count(), initial_profile_count)

        self.assertIn("sales_profile_form", response.context)
        form = response.context["sales_profile_form"]
        self.assertIn("name", form.errors)
        self.assertIn("email", form.errors)

    @mock.patch("django.contrib.messages.success")
    @mock.patch("django.contrib.messages.error")
    def test_post_requires_drivers_license(self, mock_error, mock_success):
        self.inventory_settings.require_drivers_license = True
        self.inventory_settings.save()

        temp_booking = self._create_temp_booking_in_session(self.client)

        post_data_missing_license = {
            "name": "License Required",
            "email": "license@example.com",
            "phone_number": "0412345678",
            "date_of_birth": "",
            "drivers_license_number": "",
            "drivers_license_expiry": "",
        }
        response = self.client.post(self.url, data=post_data_missing_license)
        self.assertEqual(response.status_code, 200)
        form = response.context["sales_profile_form"]
        self.assertIn("drivers_license_number", form.errors)
        self.assertIn("drivers_license_expiry", form.errors)
        self.assertIn("drivers_license_image", form.errors)
        self.assertIn("date_of_birth", form.errors)

    @mock.patch("django.contrib.messages.success")
    @mock.patch("django.contrib.messages.error")
    def test_post_requires_address_info(self, mock_error, mock_success):
        self.inventory_settings.require_address_info = True
        self.inventory_settings.save()

        temp_booking = self._create_temp_booking_in_session(self.client)

        post_data_missing_address = {
            "name": "Address Required",
            "email": "address@example.com",
            "phone_number": "0412345678",
            "date_of_birth": "1990-01-01",
            "address_line_1": "",
            "city": "",
            "state": "",
            "post_code": "",
            "country": "",
        }
        response = self.client.post(self.url, data=post_data_missing_address)
        self.assertEqual(response.status_code, 200)
        form = response.context["sales_profile_form"]
        self.assertIn("address_line_1", form.errors)
        self.assertIn("city", form.errors)
        self.assertIn("state", form.errors)
        self.assertIn("post_code", form.errors)
        self.assertIn("country", form.errors)

        mock_error.assert_called_once_with(mock.ANY, "Please correct the errors below.")
        mock_error.reset_mock()

        post_data_with_address = {
            "name": "Address Provided",
            "email": "address_ok@example.com",
            "phone_number": "0412345678",
            "date_of_birth": "1990-01-01",
            "address_line_1": "123 Main St",
            "city": "Sydney",
            "state": "NSW",
            "post_code": "2000",
            "country": "AU",
        }
        response = self.client.post(self.url, data=post_data_with_address, follow=True)

        self.assertRedirects(
            response, reverse("inventory:step2_booking_details_and_appointment")
        )
        mock_success.assert_called_once_with(
            mock.ANY,
            "Personal details saved. Proceed to booking details and appointment.",
        )
        mock_error.assert_not_called()

        new_profile = SalesProfile.objects.latest("created_at")
        self.assertEqual(new_profile.address_line_1, "123 Main St")
        self.assertEqual(new_profile.city, "Sydney")
        self.assertEqual(new_profile.country, "AU")
