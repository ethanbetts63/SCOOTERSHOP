from django.test import TestCase, Client
from django.urls import reverse
import json
import uuid


from ..test_helpers.model_factories import (
    MotorcycleFactory,
    TempSalesBookingFactory,
)


class AjaxMotorcycleAvailabilityCheckTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()

        cls.available_motorcycle = MotorcycleFactory(is_available=True)
        cls.unavailable_motorcycle = MotorcycleFactory(status="sold")

        cls.available_temp_booking = TempSalesBookingFactory(
            motorcycle=cls.available_motorcycle
        )

        cls.unavailable_temp_booking = TempSalesBookingFactory(
            motorcycle=cls.unavailable_motorcycle
        )

        cls.temp_booking_with_missing_motorcycle = TempSalesBookingFactory(
            motorcycle=MotorcycleFactory(is_available=True)
        )
        cls.temp_booking_with_missing_motorcycle.motorcycle.delete()

    def test_motorcycle_is_available(self):
        payload = {"temp_booking_uuid": str(self.available_temp_booking.session_uuid)}
        response = self.client.post(
            reverse("inventory:ajax_check_motorcycle_availability"),
            json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data["available"])
        self.assertEqual(data["message"], "Motorcycle is available.")

    def test_motorcycle_is_not_available(self):
        payload = {"temp_booking_uuid": str(self.unavailable_temp_booking.session_uuid)}
        response = self.client.post(
            reverse("inventory:ajax_check_motorcycle_availability"),
            json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertFalse(data["available"])
        self.assertEqual(
            data["message"], "Sorry, this motorcycle has just been reserved or sold."
        )

    def test_temp_booking_not_found(self):
        non_existent_uuid = uuid.uuid4()
        payload = {"temp_booking_uuid": str(non_existent_uuid)}
        response = self.client.post(
            reverse("inventory:ajax_check_motorcycle_availability"),
            json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)
        data = response.json()

        self.assertFalse(data["available"])
        self.assertEqual(data["message"], "Temporary booking not found.")

    def test_associated_motorcycle_not_found(self):
        payload = {
            "temp_booking_uuid": str(
                self.temp_booking_with_missing_motorcycle.session_uuid
            )
        }
        response = self.client.post(
            reverse("inventory:ajax_check_motorcycle_availability"),
            json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)
        data = response.json()

        self.assertFalse(data["available"])
        self.assertEqual(data["message"], "Associated motorcycle not found.")

    def test_missing_temp_booking_uuid_in_payload(self):
        payload = {"some_other_key": "some_value"}
        response = self.client.post(
            reverse("inventory:ajax_check_motorcycle_availability"),
            json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()

        self.assertFalse(data["available"])
        self.assertEqual(data["message"], "Temporary booking ID is required.")

    def test_invalid_json_format(self):
        invalid_json_string = "this is not json"
        response = self.client.post(
            reverse("inventory:ajax_check_motorcycle_availability"),
            invalid_json_string,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()

        self.assertFalse(data["available"])
        self.assertEqual(data["message"], "Invalid JSON format.")

    def test_http_method_not_allowed(self):
        response = self.client.get(
            reverse("inventory:ajax_check_motorcycle_availability")
        )
        self.assertEqual(response.status_code, 405)
