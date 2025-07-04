import datetime
from decimal import Decimal

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone

from service.models import (
    TempServiceBooking,
    ServiceBooking,
)
from dashboard.models import SiteSettings
from ..test_helpers.model_factories import (
    ServiceSettingsFactory,
    ServiceTypeFactory,
    ServiceBrandFactory,
    UserFactory,
    ServiceProfileFactory,
    CustomerMotorcycleFactory,
)


SEND_BOOKINGS_TO_MECHANICDESK = False


@override_settings(ADMIN_EMAIL="admin@example.com")
class TestLoggedInUserInStorePaymentFlow(TestCase):

    def setUp(self):
        self.client = Client()
        SiteSettings.objects.create(enable_service_booking=True)
        self.service_settings = ServiceSettingsFactory(
            enable_service_booking=True,
            enable_instore_full_payment=True,
            booking_advance_notice=1,
            drop_off_start_time=datetime.time(9, 0),
            drop_off_end_time=datetime.time(17, 0),
            booking_open_days="Mon,Tue,Wed,Thu,Fri,Sat,Sun",
        )
        self.service_type = ServiceTypeFactory(
            name="Premium Service", base_price=Decimal("250.00"), is_active=True
        )
        self.user = UserFactory(username="testuser")

        user_name = "Account In-Store User"
        if not SEND_BOOKINGS_TO_MECHANICDESK:
            user_name = "Test Account In-Store User"

        self.service_profile = ServiceProfileFactory(
            user=self.user, name=user_name, email="test@user.com", country="AU"
        )
        self.motorcycle = CustomerMotorcycleFactory(
            service_profile=self.service_profile, brand="Kawasaki", model="Ninja 400"
        )
        ServiceBrandFactory(name="Kawasaki")
        self.client.force_login(self.user)

    def test_logged_in_user_with_existing_bike_flow(self):
        step1_url = reverse("service:service_book_step1")
        step2_url = reverse("service:service_book_step2")
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
            step2_url
            + f'?temp_booking_uuid={self.client.session["temp_service_booking_uuid"]}',
        )

        step2_data = {"selected_motorcycle": self.motorcycle.id}
        response = self.client.post(step2_url, step2_data)
        self.assertRedirects(response, step4_url)

        step4_data = {
            "name": self.service_profile.name,
            "email": self.service_profile.email,
            "phone_number": self.service_profile.phone_number,
            "address_line_1": self.service_profile.address_line_1,
            "address_line_2": self.service_profile.address_line_2,
            "city": self.service_profile.city,
            "state": self.service_profile.state,
            "post_code": self.service_profile.post_code,
            "country": self.service_profile.country,
        }
        response = self.client.post(step4_url, step4_data)
        self.assertRedirects(response, step5_url)

        temp_booking = TempServiceBooking.objects.get(
            session_uuid=self.client.session["temp_service_booking_uuid"]
        )
        self.assertEqual(temp_booking.service_profile, self.service_profile)
        self.assertEqual(temp_booking.customer_motorcycle, self.motorcycle)

        step5_data = {
            "dropoff_date": valid_future_date.strftime("%Y-%m-%d"),
            "dropoff_time": "11:00",
            "payment_method": "in_store_full",
            "service_terms_accepted": "on",
        }
        response = self.client.post(step5_url, step5_data)
        self.assertRedirects(response, step7_url)

        self.assertEqual(ServiceBooking.objects.count(), 1)
        confirmation_response = self.client.get(step7_url)
        self.assertEqual(confirmation_response.status_code, 200)

        final_booking = ServiceBooking.objects.first()
        self.assertEqual(final_booking.service_profile, self.service_profile)
        self.assertEqual(final_booking.customer_motorcycle, self.motorcycle)
        self.assertContains(
            confirmation_response, final_booking.service_booking_reference
        )

        self.assertIn("last_booking_successful_timestamp", self.client.session)
