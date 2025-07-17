import datetime
from decimal import Decimal
import time

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone

from service.models import (
    ServiceBooking,
)
from dashboard.models import SiteSettings
from service.tests.test_helpers.model_factories import ServiceTypeFactory, ServiceSettingsFactory, ServiceTermsFactory, ServiceBrandFactory


SEND_BOOKINGS_TO_MECHANICDESK = False


@override_settings(ADMIN_EMAIL="admin@example.com")
class TestAnonymousInStorePaymentFlow(TestCase):

    def setUp(self):
        self.client = Client()
        SiteSettings.objects.create(enable_service_booking=True)
        self.service_settings = ServiceSettingsFactory(
            enable_instore_full_payment=True,
            booking_advance_notice=1,
            drop_off_start_time=datetime.time(9, 0),
            drop_off_end_time=datetime.time(17, 0),
            booking_open_days="Mon,Tue,Wed,Thu,Fri,Sat,Sun",
        )
        self.service_type = ServiceTypeFactory(
            name="Anonymous Basic Service", base_price=Decimal("150.00"), is_active=True
        )
        ServiceBrandFactory(name="Honda")
        ServiceTermsFactory(is_active=True)

    def test_anonymous_user_in_store_payment_flow(self):
        service_page_url = reverse("service:service")
        step1_url = reverse("service:service_book_step1")
        step3_url = reverse("service:service_book_step3")
        step4_url = reverse("service:service_book_step4")
        step5_url = reverse("service:service_book_step5")
        step7_url = reverse("service:service_book_step7")

        valid_future_date = timezone.now().date() + datetime.timedelta(
            days=self.service_settings.booking_advance_notice + 5
        )

        step1_data = {
            "service_type": self.service_type.id,
            "service_date": valid_future_date.strftime("%Y-%m-%d"),
        }
        response = self.client.post(step1_url, step1_data, follow=True)
        self.assertRedirects(
            response,
            step3_url
            + f'?temp_booking_uuid={self.client.session["temp_service_booking_uuid"]}',
        )

        motorcycle_data = {
            "brand": "Honda",
            "model": "CBR500R",
            "year": "2022",
            "engine_size": "471cc",
            "rego": "ANONR1",
            "odometer": 1500,
            "transmission": "MANUAL",
            "vin_number": "VINANONINSTORE123",
        }
        response = self.client.post(step3_url, motorcycle_data)
        self.assertRedirects(response, step4_url)

        response = self.client.get(step3_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["form"].initial["rego"], motorcycle_data["rego"]
        )

        response = self.client.post(step3_url, motorcycle_data)
        self.assertRedirects(response, step4_url)

        user_name = "Anonymous In-Store User"
        if not SEND_BOOKINGS_TO_MECHANICDESK:
            user_name = "Test Anonymous In-Store User"

        profile_data = {
            "name": user_name,
            "email": "anon.instore@user.com",
            "phone_number": "0487654321",
            "address_line_1": "456 Anon St",
            "address_line_2": "",
            "city": "Melbourne",
            "state": "VIC",
            "post_code": "3000",
            "country": "AU",
        }
        response = self.client.post(step4_url, profile_data)
        self.assertRedirects(response, step5_url)

        response = self.client.get(step4_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["form"].initial["email"], profile_data["email"]
        )

        response = self.client.post(step4_url, profile_data)
        self.assertRedirects(response, step5_url)

        step5_data = {
            "dropoff_date": valid_future_date.strftime("%Y-%m-%d"),
            "dropoff_time": "10:00",
            "payment_method": "in_store_full",
            "service_terms_accepted": "on",
        }
        response = self.client.post(step5_url, step5_data)
        self.assertRedirects(response, step7_url)

        self.assertEqual(ServiceBooking.objects.count(), 1)
        confirmation_response = self.client.get(step7_url)
        self.assertEqual(confirmation_response.status_code, 200)

        final_booking = ServiceBooking.objects.first()
        self.assertEqual(final_booking.payment_status, "unpaid")
        self.assertContains(
            confirmation_response, final_booking.service_booking_reference
        )
        self.assertIn("last_booking_successful_timestamp", self.client.session)

        response = self.client.post(
            step1_url,
            {
                "service_type": self.service_type.id,
                "service_date": valid_future_date.strftime("%Y-%m-%d"),
            },
            follow=True,
        )
        self.assertRedirects(response, service_page_url)
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]),
            "You recently completed a booking. If you wish to make another, please ensure your previous booking was processed successfully or wait a few moments.",
        )

        session = self.client.session
        session["last_booking_successful_timestamp"] = time.time() - 300
        session.save()

        response = self.client.post(
            step1_url,
            {
                "service_type": self.service_type.id,
                "service_date": valid_future_date.strftime("%Y-%m-%d"),
            },
            follow=True,
        )
        self.assertRedirects(
            response,
            step3_url
            + f'?temp_booking_uuid={self.client.session["temp_service_booking_uuid"]}',
        )
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertIn("Service details selected", str(messages[0]))
