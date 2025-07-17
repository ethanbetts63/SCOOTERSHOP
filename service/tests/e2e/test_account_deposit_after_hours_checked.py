import datetime
from decimal import Decimal
import stripe
from unittest import skipIf

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.conf import settings
from django.utils import timezone

from service.models import (
    TempServiceBooking,
    ServiceBooking,
)
from dashboard.models import SiteSettings
from payments.models import Payment
from payments.webhook_handlers.service_handlers import handle_service_booking_succeeded
from users.tests.test_helpers.model_factories import UserFactory
from service.tests.test_helpers.model_factories import ServiceProfileFactory, ServiceTypeFactory, ServiceSettingsFactory, ServiceTermsFactory, CustomerMotorcycleFactory, ServiceBrandFactory



SEND_BOOKINGS_TO_MECHANICDESK = False


@skipIf(not settings.STRIPE_SECRET_KEY, "Stripe API key not configured in settings")
@override_settings(ADMIN_EMAIL="admin@example.com")
class TestAfterHoursDepositPaymentFlow(TestCase):
    """
    Tests the entire service booking flow for a logged-in user who
    selects the after-hours drop-off option and pays a deposit.
    This test is based on the standard TestLoggedInDepositPaymentFlow.
    """

    def setUp(self):
        self.client = Client()
        SiteSettings.objects.create()
        self.deposit_amount = Decimal("75.00")
        self.service_settings = ServiceSettingsFactory(
            enable_online_deposit=True,
            deposit_calc_method="FLAT_FEE",
            deposit_flat_fee_amount=self.deposit_amount,
            booking_advance_notice=1,
            drop_off_start_time=datetime.time(9, 0),
            drop_off_end_time=datetime.time(17, 0),
            booking_open_days="Mon,Tue,Wed,Thu,Fri,Sat,Sun",
            currency_code="AUD",
            # --- Key setting for this test ---
            enable_after_hours_dropoff=True,
        )
        self.service_type = ServiceTypeFactory(
            name="After Hours Test Service", base_price=Decimal("600.00"), is_active=True
        )
        self.user = UserFactory(username="afterhoursuser")

        user_name = "After Hours User"
        if not SEND_BOOKINGS_TO_MECHANICDESK:
            user_name = "Test After Hours User"

        self.service_profile = ServiceProfileFactory(
            user=self.user, name=user_name, email="after.hours@user.com", country="AU"
        )
        self.motorcycle = CustomerMotorcycleFactory(
            service_profile=self.service_profile, brand="Yamaha", model="MT-07"
        )
        ServiceBrandFactory(name="Yamaha")
        self.client.force_login(self.user)
        stripe.api_key = settings.STRIPE_SECRET_KEY
        ServiceTermsFactory(is_active=True)

    def test_logged_in_user_after_hours_deposit_flow(self):
        # --- URL and Date Setup ---
        step1_url = reverse("service:service_book_step1")
        step2_url = reverse("service:service_book_step2")
        step4_url = reverse("service:service_book_step4")
        step5_url = reverse("service:service_book_step5")
        step6_url = reverse("service:service_book_step6")
        step7_url = reverse("service:service_book_step7")

        valid_future_date = timezone.now().date() + datetime.timedelta(
            days=self.service_settings.booking_advance_notice + 5
        )

        # --- Step 1 & 2: Service and Motorcycle Selection ---
        self.client.post(
            step1_url,
            {
                "service_type": self.service_type.id,
                "service_date": valid_future_date.strftime("%Y-%m-%d"),
            },
            follow=True,
        )
        self.client.post(
            step2_url, {"selected_motorcycle": self.motorcycle.id}
        )

        # --- Step 4: Profile Confirmation ---
        profile_data = {
            "name": self.service_profile.name,
            "email": self.service_profile.email,
            "phone_number": self.service_profile.phone_number,
        }
        self.client.post(step4_url, profile_data)

        # --- Step 5: Payment and Drop-off Details ---
        # ** This is the critical change for the test **
        step5_data = {
            "dropoff_date": valid_future_date.strftime("%Y-%m-%d"),
            "after_hours_drop_off_choice": "on", # Check the after-hours box
            "dropoff_time": "", # Ensure time is empty as per form logic
            "payment_method": "online_deposit",
            "service_terms_accepted": "on",
        }
        response = self.client.post(step5_url, step5_data)
        self.assertRedirects(response, step6_url)

        # --- Step 6: Mock Payment Page & Stripe Confirmation ---
        self.client.get(step6_url)
        self.assertEqual(Payment.objects.count(), 1)
        payment_obj = Payment.objects.first()
        payment_intent_id = payment_obj.stripe_payment_intent_id
        self.assertEqual(payment_obj.amount, self.deposit_amount)

        try:
            confirmation_url_path = reverse("service:service_book_step7")
            full_return_url = f"http://testserver{confirmation_url_path}"
            stripe.PaymentIntent.confirm(
                payment_intent_id,
                payment_method="pm_card_visa",
                return_url=full_return_url,
            )
        except stripe.error.StripeError as e:
            self.fail(f"Stripe API call failed during test: {e}")

        # --- Webhook Simulation & Final Assertions ---
        updated_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        handle_service_booking_succeeded(payment_obj, updated_intent)

        self.assertEqual(ServiceBooking.objects.count(), 1)
        self.assertEqual(TempServiceBooking.objects.count(), 0)
        final_booking = ServiceBooking.objects.first()

        # ** Assertions specific to the after-hours flow **
        self.assertTrue(final_booking.after_hours_drop_off)
        self.assertIsNone(final_booking.dropoff_time)

        # Standard assertions from the original test
        self.assertEqual(final_booking.payment_status, "deposit_paid")
        self.assertEqual(final_booking.amount_paid, self.deposit_amount)
        self.assertEqual(final_booking.calculated_total, self.service_type.base_price)
        self.assertEqual(final_booking.service_profile, self.service_profile)
        self.assertEqual(final_booking.customer_motorcycle, self.motorcycle)

        # --- Step 7: Confirmation Page ---
        confirmation_url_with_param = (
            f"{step7_url}?payment_intent_id={payment_intent_id}"
        )
        confirmation_response = self.client.get(confirmation_url_with_param)
        self.assertEqual(confirmation_response.status_code, 200)
        self.assertContains(
            confirmation_response, final_booking.service_booking_reference
        )
        self.assertIn("last_booking_successful_timestamp", self.client.session)
