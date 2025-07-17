from decimal import Decimal
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from inventory.models import TempSalesBooking, SalesBooking
from inventory.tests.test_helpers.model_factories import InventorySettingsFactory, MotorcycleFactory, SalesTermsFactory
from users.tests.test_helpers.model_factories import UserFactory

@override_settings(ADMIN_EMAIL="ethan.betts.dev@gmail.com")
class TestEnquiryWithAppointmentFlow(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = UserFactory()
        self.client.force_login(self.user)
        self.settings = InventorySettingsFactory(currency_code="AUD")
        self.motorcycle = MotorcycleFactory(
            status="for_sale",
            price=Decimal("5000.00"),
            year=1993,
            brand="Kawasaki",
            model="Enough",
        )
        self.another_motorcycle = MotorcycleFactory(
            status="for_sale", price=Decimal("8000.00")
        )
        self.sales_terms = SalesTermsFactory(is_active=True)

    def test_enquiry_with_appointment_flow(self):
        initiate_url = reverse(
            "inventory:initiate_booking", kwargs={"pk": self.motorcycle.pk}
        )
        response = self.client.post(
            initiate_url, {"deposit_required_for_flow": "false"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("temp_sales_booking_uuid", self.client.session)

        step1_url = reverse("inventory:step1_sales_profile")
        step2_url = reverse("inventory:step2_booking_details_and_appointment")

        profile_data = {
            "name": "Enquiry User",
            "email": "enquiry@example.com",
            "phone_number": "555-0000",
        }
        response = self.client.post(step1_url, profile_data)
        self.assertRedirects(response, step2_url)

        self.client.get(step1_url)
        updated_profile_data = {
            "name": "Enquiry User Updated",
            "email": "enquiry@example.com",
            "phone_number": "555-1111",
        }
        response = self.client.post(step1_url, updated_profile_data)
        self.assertRedirects(response, step2_url)

        appointment_data = {
            "appointment_date": "2025-10-20",
            "appointment_time": "10:00",
            "terms_accepted": "on",
            "customer_notes": "I would like to come see this bike.",
        }
        response = self.client.post(step2_url, appointment_data)

        self.assertRedirects(response, reverse("inventory:step4_confirmation"))
        self.assertEqual(TempSalesBooking.objects.count(), 0)
        self.assertEqual(SalesBooking.objects.count(), 1)

        final_booking = SalesBooking.objects.first()
        self.assertEqual(final_booking.sales_profile.name, "Enquiry User Updated")
        self.assertEqual(final_booking.sales_profile.phone_number, "555-1111")
        self.assertIsNotNone(final_booking.appointment_date)

        confirmation_response = self.client.get(response.url)
        self.assertEqual(confirmation_response.status_code, 200)
        self.assertContains(
            confirmation_response, final_booking.sales_booking_reference
        )
        self.assertIn("last_sales_booking_timestamp", self.client.session)