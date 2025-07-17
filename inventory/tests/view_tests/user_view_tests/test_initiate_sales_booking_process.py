from django.test import TestCase, Client
from django.urls import reverse
from inventory.models import TempSalesBooking


from inventory.tests.test_helpers.model_factories import (
    MotorcycleFactory,
    InventorySettingsFactory,
)


class InitiateBookingProcessViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()

        cls.inventory_settings = InventorySettingsFactory()

        cls.motorcycle = MotorcycleFactory(status="for_sale")

        cls.initiate_booking_url = reverse(
            "inventory:initiate_booking", kwargs={"pk": cls.motorcycle.pk}
        )

    def test_post_request_creates_temp_booking_deposit_flow(self):
        initial_temp_booking_count = TempSalesBooking.objects.count()

        data = {
            "deposit_required_for_flow": "true",
        }
        response = self.client.post(self.initiate_booking_url, data)

        self.assertEqual(
            TempSalesBooking.objects.count(), initial_temp_booking_count + 1
        )

        temp_booking = TempSalesBooking.objects.latest("created_at")

        self.assertEqual(temp_booking.motorcycle, self.motorcycle)
        self.assertTrue(temp_booking.deposit_required_for_flow)
        self.assertEqual(temp_booking.booking_status, "pending_details")

        self.assertRedirects(response, reverse("inventory:step1_sales_profile"))

        self.assertIn("temp_sales_booking_uuid", self.client.session)

        self.assertEqual(
            self.client.session["temp_sales_booking_uuid"],
            str(temp_booking.session_uuid),
        )

    def test_post_request_creates_temp_booking_enquiry_flow(self):
        initial_temp_booking_count = TempSalesBooking.objects.count()

        data = {
            "deposit_required_for_flow": "false",
        }
        response = self.client.post(self.initiate_booking_url, data)

        self.assertEqual(
            TempSalesBooking.objects.count(), initial_temp_booking_count + 1
        )

        temp_booking = TempSalesBooking.objects.latest("created_at")
        self.assertEqual(temp_booking.motorcycle, self.motorcycle)
        self.assertFalse(temp_booking.deposit_required_for_flow)
        self.assertEqual(temp_booking.booking_status, "pending_details")

        self.assertRedirects(response, reverse("inventory:step1_sales_profile"))
        self.assertIn("temp_sales_booking_uuid", self.client.session)

        self.assertEqual(
            self.client.session["temp_sales_booking_uuid"],
            str(temp_booking.session_uuid),
        )

    def test_post_request_creates_temp_booking_with_viewing_request(self):
        initial_temp_booking_count = TempSalesBooking.objects.count()

        data = {
            "deposit_required_for_flow": "false",
        }
        response = self.client.post(self.initiate_booking_url, data)

        self.assertEqual(
            TempSalesBooking.objects.count(), initial_temp_booking_count + 1
        )

        temp_booking = TempSalesBooking.objects.latest("created_at")
        self.assertEqual(temp_booking.motorcycle, self.motorcycle)
        self.assertFalse(temp_booking.deposit_required_for_flow)
        self.assertEqual(temp_booking.booking_status, "pending_details")

        self.assertRedirects(response, reverse("inventory:step1_sales_profile"))
        self.assertIn("temp_sales_booking_uuid", self.client.session)

        self.assertEqual(
            self.client.session["temp_sales_booking_uuid"],
            str(temp_booking.session_uuid),
        )

    def test_post_request_non_existent_motorcycle_pk(self):
        non_existent_pk = self.motorcycle.pk + 999
        url = reverse("inventory:initiate_booking", kwargs={"pk": non_existent_pk})

        data = {
            "deposit_required_for_flow": "false",
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 404)
