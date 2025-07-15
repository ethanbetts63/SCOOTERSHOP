import datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.messages import get_messages
from unittest import mock
import json
from inventory.models import InventorySettings
from inventory.forms.sales_booking_appointment_form import BookingAppointmentForm
from ...test_helpers.model_factories import (
    TempSalesBookingFactory,
    InventorySettingsFactory,
    MotorcycleFactory,
    SalesProfileFactory,
    SalesTermsFactory,
)


class Step2BookingDetailsViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.url = reverse("inventory:step2_booking_details_and_appointment")

        cls.inventory_settings = InventorySettingsFactory(
            enable_viewing_for_enquiry=True,
            enable_reservation_by_deposit=True,
            enable_sales_new_bikes=True,
        )
        cls.sales_terms = SalesTermsFactory(is_active=True)

        cls.motorcycle = MotorcycleFactory(condition="new")
        cls.sales_profile = SalesProfileFactory()

    def _create_temp_booking_in_session(self, client, **kwargs):
        default_kwargs = {
            "motorcycle": self.motorcycle,
            "sales_profile": self.sales_profile,
            "booking_status": "pending_details",
            "deposit_required_for_flow": self.inventory_settings.enable_reservation_by_deposit,
            "appointment_date": None,
            "appointment_time": None,
            "customer_notes": "",
            "terms_accepted": False,
        }
        default_kwargs.update(kwargs)

        temp_booking = TempSalesBookingFactory(**default_kwargs)
        temp_booking.save() # Ensure the deposit_required_for_flow is saved
        session = client.session
        session["temp_sales_booking_uuid"] = str(temp_booking.session_uuid)
        session.save()
        return temp_booking

    def test_get_no_temp_booking_id_in_session(self):
        response = self.client.get(self.url, follow=True)
        self.assertRedirects(response, reverse("core:index"))
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
        self.assertRedirects(response, reverse("core:index"))
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
        self.assertRedirects(response, reverse("core:index"))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]),
            "Inventory settings are not configured. Please contact support.",
        )

        self.inventory_settings = InventorySettingsFactory(pk=1)

    def test_get_success_initial_form_data(self):
        test_date = datetime.date.today() + datetime.timedelta(days=7)
        test_time = datetime.time(10, 30)
        temp_booking = self._create_temp_booking_in_session(
            self.client,
            appointment_date=test_date,
            appointment_time=test_time,
            customer_notes="Test notes for viewing.",
            terms_accepted=True,
        )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "inventory/step2_booking_details.html")
        self.assertIn("form", response.context)
        self.assertIn("temp_booking", response.context)
        self.assertIn("inventory_settings", response.context)
        self.assertIn("min_appointment_date", response.context)
        self.assertIn("max_appointment_date", response.context)
        self.assertIn("blocked_appointment_dates_json", response.context)

        form = response.context["form"]
        self.assertTrue(isinstance(form, BookingAppointmentForm))

        self.assertEqual(form["appointment_date"].value(), test_date)
        self.assertEqual(form["appointment_time"].value(), test_time)
        self.assertEqual(form["customer_notes"].value(), "Test notes for viewing.")
        self.assertEqual(form["terms_accepted"].value(), True)

        self.assertEqual(response.context["temp_booking"], temp_booking)
        self.assertEqual(
            response.context["inventory_settings"], self.inventory_settings
        )
        self.assertIsNotNone(response.context["min_appointment_date"])
        self.assertIsNotNone(response.context["max_appointment_date"])
        self.assertIsNotNone(response.context["blocked_appointment_dates_json"])
        self.assertTrue(
            json.loads(response.context["blocked_appointment_dates_json"]) is not None
        )

    @mock.patch("django.contrib.messages.success")
    @mock.patch("django.contrib.messages.error")
    def test_post_no_temp_booking_id_in_session(self, mock_error, mock_success):
        response = self.client.post(self.url, data={}, follow=True)
        self.assertRedirects(response, reverse("core:index"))
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

        response = self.client.post(
            self.url, data={"terms_accepted": "on"}, follow=True
        )
        self.assertRedirects(response, reverse("core:index"))
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

        response = self.client.post(
            self.url, data={"terms_accepted": "on"}, follow=True
        )
        self.assertRedirects(response, reverse("core:index"))
        mock_error.assert_called_once_with(
            mock.ANY, "Inventory settings are not configured. Please contact support."
        )
        mock_success.assert_not_called()

        self.inventory_settings = InventorySettingsFactory(pk=1)

    @mock.patch("inventory.utils.convert_temp_sales_booking.convert_temp_sales_booking")
    @mock.patch("django.contrib.messages.success")
    @mock.patch("django.contrib.messages.error")
    def test_post_valid_data_deposit_required(
        self, mock_error, mock_success, mock_convert_temp_sales_booking
    ):
        # Directly create and save TempSalesBooking to ensure deposit_required_for_flow is True
        # Ensure an active SalesTerms exists for the test
        SalesTermsFactory(is_active=True) # Ensure one exists

        temp_booking = TempSalesBookingFactory(
            motorcycle=self.motorcycle,
            sales_profile=self.sales_profile,
            deposit_required_for_flow=True,
            booking_status="pending_details",
            sales_terms_version=self.sales_terms, # Link to the active sales terms
        )
        temp_booking.save()

        # Manually set the session UUID
        session = self.client.session
        session["temp_sales_booking_uuid"] = str(temp_booking.session_uuid)
        session.save()

        post_date = datetime.date.today() + datetime.timedelta(days=10)
        post_time = datetime.time(14, 0)
        post_data = {
            "appointment_date": post_date.strftime("%Y-%m-%d"),
            "appointment_time": post_time.strftime("%H:%M"),
            "customer_notes": "Looking forward to the viewing.",
            "terms_accepted": "on",
        }

        response = self.client.post(self.url, data=post_data, follow=True)

        self.assertRedirects(response, reverse("inventory:step3_payment"))
        mock_success.assert_called_once_with(
            mock.ANY, "Booking details saved. Proceed to payment."
        )
        mock_error.assert_not_called()
        mock_convert_temp_sales_booking.assert_not_called()

        temp_booking.refresh_from_db()
        self.assertEqual(temp_booking.appointment_date, post_date)
        self.assertEqual(temp_booking.appointment_time, post_time)
        self.assertEqual(temp_booking.customer_notes, "Looking forward to the viewing.")
        self.assertTrue(temp_booking.terms_accepted)

    @mock.patch("django.contrib.messages.success")
    @mock.patch("django.contrib.messages.error")
    def test_post_invalid_data(self, mock_error, mock_success):
        temp_booking = self._create_temp_booking_in_session(self.client)

        post_data = {
            "appointment_date": (
                datetime.date.today() + datetime.timedelta(days=1)
            ).strftime("%Y-%m-%d"),
            "appointment_time": datetime.time(11, 0).strftime("%H:%M"),
            "customer_notes": "Invalid submission test.",
        }
        response = self.client.post(self.url, data=post_data)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "inventory/step2_booking_details.html")
        mock_error.assert_called_once_with(mock.ANY, "Please correct the errors below.")
        mock_success.assert_not_called()

        self.assertIn("form", response.context)
        form = response.context["form"]
        self.assertIn("terms_accepted", form.errors)

        temp_booking_before_post = temp_booking
        temp_booking.refresh_from_db()
        self.assertEqual(
            temp_booking.appointment_date, temp_booking_before_post.appointment_date
        )
        self.assertEqual(
            temp_booking.appointment_time, temp_booking_before_post.appointment_time
        )

    @mock.patch("django.contrib.messages.success")
    @mock.patch("django.contrib.messages.error")
    def test_post_invalid_date_or_time_format(self, mock_error, mock_success):
        temp_booking = self._create_temp_booking_in_session(self.client)

        post_data = {
            "appointment_date": "2023/12/30",
            "appointment_time": "25:00",
            "customer_notes": "Bad date/time test.",
            "terms_accepted": "on",
        }
        response = self.client.post(self.url, data=post_data)
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertIn("appointment_date", form.errors)
        self.assertIn("appointment_time", form.errors)
        mock_error.assert_called_once_with(mock.ANY, "Please correct the errors below.")
        mock_success.assert_not_called()

    @mock.patch("django.contrib.messages.success")
    @mock.patch("django.contrib.messages.error")
    def test_post_appointment_required_for_viewing(self, mock_error, mock_success):
        temp_booking = self._create_temp_booking_in_session(self.client)

        post_data = {
            "appointment_date": "",
            "appointment_time": "",
            "customer_notes": "Viewing requested but no details.",
            "terms_accepted": "on",
        }
        response = self.client.post(self.url, data=post_data)
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertIn("appointment_date", form.errors)
        self.assertIn("appointment_time", form.errors)
        mock_error.assert_called_once_with(mock.ANY, "Please correct the errors below.")
        mock_success.assert_not_called()
