from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.messages import get_messages
from django.contrib.auth import get_user_model
import datetime
import uuid
import json
from unittest.mock import patch, MagicMock
from decimal import Decimal
import stripe
from payments.models import Payment
from service.models import (
    TempServiceBooking,
    ServiceProfile,
    CustomerMotorcycle,
)
from users.tests.test_helpers.model_factories import UserFactory
from service.tests.test_helpers.model_factories import TempServiceBookingFactory, ServiceProfileFactory, ServiceTypeFactory, ServiceSettingsFactory, CustomerMotorcycleFactory
from payments.tests.test_helpers.model_factories import PaymentFactory

User = get_user_model()


def get_next_available_weekday(start_date, open_days):
    day_map = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}
    open_weekdays = {day_map[day] for day in open_days}

    current_date = start_date
    while current_date.weekday() not in open_weekdays:
        current_date += datetime.timedelta(days=1)
    return current_date


@patch("stripe.api_key", "sk_test_mock_key")
class Step6PaymentViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.factory = RequestFactory()
        cls.user_password = "testpassword123"
        cls.user = UserFactory(password=cls.user_password)

        cls.service_settings = ServiceSettingsFactory(
            enable_online_full_payment=True,
            enable_online_deposit=True,
            enable_instore_full_payment=True,
            currency_code="AUD",
            booking_open_days="Mon,Tue,Wed,Thu,Fri",
        )
        cls.service_type = ServiceTypeFactory(base_price=Decimal("250.00"))
        cls.base_url = reverse("service:service_book_step6")

    def setUp(self):
        TempServiceBooking.objects.all().delete()
        Payment.objects.all().delete()
        ServiceProfile.objects.all().delete()
        CustomerMotorcycle.objects.all().delete()

        self.customer_motorcycle = CustomerMotorcycleFactory(
            brand="TestBrand", model="TestModel", year=2020, rego="TESTMC"
        )
        self.service_profile = ServiceProfileFactory(
            user=self.user, email="test@example.com"
        )

        start_date = datetime.date.today() + datetime.timedelta(days=5)
        open_days = [
            d.strip() for d in self.service_settings.booking_open_days.split(",")
        ]
        available_date = get_next_available_weekday(start_date, open_days)

        self.temp_booking = TempServiceBookingFactory(
            service_type=self.service_type,
            service_date=available_date,
            dropoff_date=available_date,
            dropoff_time=datetime.time(10, 0),
            customer_motorcycle=self.customer_motorcycle,
            service_profile=self.service_profile,
            payment_method="online_full",
            calculated_deposit_amount=Decimal("50.00"),
        )

        session = self.client.session
        session["temp_service_booking_uuid"] = str(self.temp_booking.session_uuid)
        session.save()

    def test_dispatch_no_temp_booking_uuid_in_session_redirects_to_service_home(self):

        self.client.logout()
        session = self.client.session
        if "temp_service_booking_uuid" in session:
            del session["temp_service_booking_uuid"]
        session.save()

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response, reverse("service:service"), fetch_redirect_response=False
        )
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                "Your booking session has expired or is invalid." in str(m)
                for m in messages
            )
        )

    def test_dispatch_invalid_temp_booking_uuid_redirects_to_service_home(self):

        session = self.client.session
        session["temp_service_booking_uuid"] = str(uuid.uuid4())
        session.save()

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response, reverse("service:service"), fetch_redirect_response=False
        )
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any("Your booking session could not be found." in str(m) for m in messages)
        )

    def test_dispatch_no_customer_motorcycle_redirects_to_step3(self):

        self.temp_booking.customer_motorcycle = None
        self.temp_booking.save()

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse("service:service_book_step3"),
            fetch_redirect_response=False,
        )
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                "Please select or add your motorcycle details first (Step 3)." in str(m)
                for m in messages
            )
        )

    def test_dispatch_no_service_profile_redirects_to_step4(self):

        self.temp_booking.service_profile = None
        self.temp_booking.save()

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse("service:service_book_step4"),
            fetch_redirect_response=False,
        )
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                "Please provide your contact details first (Step 4)." in str(m)
                for m in messages
            )
        )

    @patch(
        "service.views.step6_payment_view.get_service_date_availability",
        return_value=(datetime.date.today(), "[]"),
    )
    def test_dispatch_valid_temp_booking_proceeds(self, mock_availability):

        with patch("stripe.PaymentIntent.create") as mock_create:
            mock_create.return_value = MagicMock(
                client_secret="test_client_secret",
                id="pi_new_123",
                status="requires_payment_method",
            )
            response = self.client.get(self.base_url)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, "service/step6_payment.html")
            mock_create.assert_called_once()

    @patch("stripe.PaymentIntent.create")
    @patch("stripe.PaymentIntent.retrieve")
    @patch("stripe.PaymentIntent.modify")
    def test_get_online_full_payment_creates_new_intent_and_payment_obj(
        self, mock_modify, mock_retrieve, mock_create
    ):

        self.temp_booking.payment_method = "online_full"
        self.temp_booking.save()

        mock_create.return_value = MagicMock(
            client_secret="new_client_secret",
            id="pi_new_full_123",
            status="requires_payment_method",
        )
        mock_retrieve.side_effect = stripe.error.InvalidRequestError(
            "No such payment intent", "id"
        )

        response = self.client.get(self.base_url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("client_secret", response.context)
        self.assertEqual(response.context["client_secret"], "new_client_secret")
        self.assertEqual(response.context["amount"], self.service_type.base_price)
        self.assertEqual(response.context["currency"], "AUD")
        self.assertTemplateUsed(response, "service/step6_payment.html")

        mock_create.assert_called_once_with(
            amount=int(self.service_type.base_price * 100),
            currency="AUD",
            metadata={
                "temp_service_booking_uuid": str(self.temp_booking.session_uuid),
                "service_profile_id": str(self.service_profile.id),
                "booking_type": "service_booking",
            },
            description=f"Motorcycle service booking for {self.customer_motorcycle.year} {self.customer_motorcycle.brand} {self.customer_motorcycle.model} ({self.service_type.name})",
        )

        payment = Payment.objects.get(temp_service_booking=self.temp_booking)
        self.assertEqual(payment.stripe_payment_intent_id, "pi_new_full_123")
        self.assertEqual(payment.amount, self.service_type.base_price)
        self.assertEqual(payment.currency, "AUD")
        self.assertEqual(payment.status, "requires_payment_method")
        self.assertEqual(payment.service_customer_profile, self.service_profile)
        self.assertEqual(Payment.objects.count(), 1)

    @patch("stripe.PaymentIntent.create")
    @patch("stripe.PaymentIntent.retrieve")
    @patch("stripe.PaymentIntent.modify")
    def test_get_online_deposit_creates_new_intent_and_payment_obj(
        self, mock_modify, mock_retrieve, mock_create
    ):

        self.temp_booking.payment_method = "online_deposit"
        self.temp_booking.save()

        mock_create.return_value = MagicMock(
            client_secret="new_deposit_secret",
            id="pi_new_deposit_456",
            status="requires_payment_method",
        )
        mock_retrieve.side_effect = stripe.error.InvalidRequestError(
            "No such payment intent", "id"
        )

        response = self.client.get(self.base_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["client_secret"], "new_deposit_secret")
        self.assertEqual(
            response.context["amount"], self.temp_booking.calculated_deposit_amount
        )
        self.assertEqual(response.context["currency"], "AUD")

        mock_create.assert_called_once_with(
            amount=int(self.temp_booking.calculated_deposit_amount * 100),
            currency="AUD",
            metadata={
                "temp_service_booking_uuid": str(self.temp_booking.session_uuid),
                "service_profile_id": str(self.service_profile.id),
                "booking_type": "service_booking",
            },
            description=f"Motorcycle service booking for {self.customer_motorcycle.year} {self.customer_motorcycle.brand} {self.customer_motorcycle.model} ({self.service_type.name})",
        )

        payment = Payment.objects.get(temp_service_booking=self.temp_booking)
        self.assertEqual(payment.stripe_payment_intent_id, "pi_new_deposit_456")
        self.assertEqual(payment.amount, self.temp_booking.calculated_deposit_amount)
        self.assertEqual(payment.status, "requires_payment_method")

    @patch("stripe.PaymentIntent.create")
    @patch("stripe.PaymentIntent.retrieve")
    @patch("stripe.PaymentIntent.modify")
    def test_get_existing_intent_modified_if_amount_changed(
        self, mock_modify, mock_retrieve, mock_create
    ):

        existing_amount = Decimal("100.00")
        new_amount = Decimal("150.00")
        self.temp_booking.payment_method = "online_full"
        self.temp_booking.service_type.base_price = new_amount
        self.temp_booking.service_type.save()
        self.temp_booking.save()

        initial_payment = PaymentFactory(
            temp_service_booking=self.temp_booking,
            amount=existing_amount,
            currency="AUD",
            status="requires_payment_method",
            service_customer_profile=self.service_profile,
            stripe_payment_intent_id="pi_existing_123",
        )

        mock_retrieve.return_value = MagicMock(
            id="pi_existing_123",
            amount=int(existing_amount * 100),
            currency="aud",
            client_secret="old_client_secret",
            status="requires_payment_method",
        )
        mock_modify.return_value = MagicMock(
            id="pi_existing_123",
            amount=int(new_amount * 100),
            currency="aud",
            client_secret="new_client_secret_modified",
            status="requires_action",
        )

        response = self.client.get(self.base_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["client_secret"], "new_client_secret_modified"
        )
        self.assertEqual(response.context["amount"], new_amount)

        mock_retrieve.assert_called_once_with("pi_existing_123")
        mock_modify.assert_called_once_with(
            "pi_existing_123",
            amount=int(new_amount * 100),
            currency="AUD",
            description=f"Motorcycle service booking for {self.customer_motorcycle.year} {self.customer_motorcycle.brand} {self.customer_motorcycle.model} ({self.service_type.name})",
            metadata={
                "temp_service_booking_uuid": str(self.temp_booking.session_uuid),
                "service_profile_id": str(self.service_profile.id),
                "booking_type": "service_booking",
            },
        )
        mock_create.assert_not_called()

        initial_payment.refresh_from_db()
        self.assertEqual(initial_payment.amount, new_amount)
        self.assertEqual(initial_payment.status, "requires_action")

    @patch("stripe.PaymentIntent.create")
    @patch("stripe.PaymentIntent.retrieve")
    @patch("stripe.PaymentIntent.modify")
    def test_get_existing_intent_succeeded_renders_with_flag(
        self, mock_modify, mock_retrieve, mock_create
    ):

        initial_payment = PaymentFactory(
            temp_service_booking=self.temp_booking,
            amount=self.service_type.base_price,
            currency="AUD",
            status="succeeded",
            service_customer_profile=self.service_profile,
            stripe_payment_intent_id="pi_succeeded_789",
        )

        mock_retrieve.return_value = MagicMock(
            id="pi_succeeded_789",
            amount=int(self.service_type.base_price * 100),
            currency="aud",
            client_secret="succeeded_client_secret",
            status="succeeded",
        )

        response = self.client.get(self.base_url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("payment_already_succeeded", response.context)
        self.assertTrue(response.context["payment_already_succeeded"])
        self.assertTemplateUsed(response, "service/step6_payment.html")

        mock_retrieve.assert_called_once_with("pi_succeeded_789")
        mock_modify.assert_not_called()
        mock_create.assert_not_called()

    @patch("stripe.PaymentIntent.create")
    @patch("stripe.PaymentIntent.retrieve")
    @patch("stripe.PaymentIntent.modify")
    def test_get_stripe_error_redirects_to_step5(
        self, mock_modify, mock_retrieve, mock_create
    ):

        mock_retrieve.side_effect = stripe.error.StripeError(
            "Stripe API error during retrieve"
        )
        mock_create.side_effect = stripe.error.StripeError(
            "Stripe API error during create"
        )

        response = self.client.get(self.base_url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse("service:service_book_step5"),
            fetch_redirect_response=False,
        )
        self.assertEqual(Payment.objects.count(), 0)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Payment system error:" in str(m) for m in messages))

    @patch("stripe.PaymentIntent.create")
    @patch("stripe.PaymentIntent.retrieve")
    @patch("stripe.PaymentIntent.modify")
    def test_get_invalid_amount_redirects_to_step5(
        self, mock_modify, mock_retrieve, mock_create
    ):

        self.temp_booking.payment_method = "online_full"
        self.temp_booking.service_type.base_price = Decimal("0.00")
        self.temp_booking.service_type.save()
        self.temp_booking.save()

        response = self.client.get(self.base_url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse("service:service_book_step5"),
            fetch_redirect_response=False,
        )
        mock_create.assert_not_called()
        mock_retrieve.assert_not_called()
        mock_modify.assert_not_called()
        self.assertEqual(Payment.objects.count(), 0)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any("The amount to pay is invalid." in str(m) for m in messages)
        )

    @patch("stripe.PaymentIntent.retrieve")
    def test_post_payment_succeeded_json_response(self, mock_retrieve):

        payment_intent_id = "pi_test_succeeded"
        payment_obj = PaymentFactory(
            temp_service_booking=self.temp_booking,
            stripe_payment_intent_id=payment_intent_id,
            status="requires_action",
            amount=self.service_type.base_price,
            currency="AUD",
            service_customer_profile=self.service_profile,
        )

        mock_retrieve.return_value = MagicMock(id=payment_intent_id, status="succeeded")

        response = self.client.post(
            self.base_url,
            json.dumps({"payment_intent_id": payment_intent_id}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertEqual(json_response["status"], "success")
        self.assertIn("redirect_url", json_response)
        self.assertTrue(
            json_response["redirect_url"].endswith(
                f"?payment_intent_id={payment_intent_id}"
            )
        )

        payment_obj.refresh_from_db()
        self.assertEqual(payment_obj.status, "requires_action")

    @patch("stripe.PaymentIntent.retrieve")
    def test_post_payment_requires_action_json_response(self, mock_retrieve):

        payment_intent_id = "pi_test_requires_action"
        payment_obj = PaymentFactory(
            temp_service_booking=self.temp_booking,
            stripe_payment_intent_id=payment_intent_id,
            status="requires_payment_method",
            amount=self.service_type.base_price,
            currency="AUD",
            service_customer_profile=self.service_profile,
        )

        mock_retrieve.return_value = MagicMock(
            id=payment_intent_id, status="requires_action"
        )

        response = self.client.post(
            self.base_url,
            json.dumps({"payment_intent_id": payment_intent_id}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertEqual(json_response["status"], "requires_action")
        self.assertIn("message", json_response)
        self.assertNotIn("redirect_url", json_response)

        payment_obj.refresh_from_db()
        self.assertEqual(payment_obj.status, "requires_payment_method")

    @patch("stripe.PaymentIntent.retrieve")
    def test_post_payment_failed_json_response(self, mock_retrieve):

        payment_intent_id = "pi_test_failed"
        payment_obj = PaymentFactory(
            temp_service_booking=self.temp_booking,
            stripe_payment_intent_id=payment_intent_id,
            status="requires_payment_method",
            amount=self.service_type.base_price,
            currency="AUD",
            service_customer_profile=self.service_profile,
        )

        mock_retrieve.return_value = MagicMock(id=payment_intent_id, status="failed")

        response = self.client.post(
            self.base_url,
            json.dumps({"payment_intent_id": payment_intent_id}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertEqual(json_response["status"], "failed")
        self.assertIn("message", json_response)
        self.assertNotIn("redirect_url", json_response)

        payment_obj.refresh_from_db()
        self.assertEqual(payment_obj.status, "requires_payment_method")

    def test_post_invalid_json_returns_400(self):

        response = self.client.post(
            self.base_url,
            '{"payment_intent_id": "pi_invalid"',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid JSON format in request body", response.json()["error"])

    def test_post_missing_payment_intent_id_returns_400(self):

        response = self.client.post(
            self.base_url,
            json.dumps({"some_other_key": "value"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Payment Intent ID is required in the request", response.json()["error"]
        )

    @patch("stripe.PaymentIntent.retrieve")
    def test_post_stripe_error_returns_500(self, mock_retrieve):

        payment_intent_id = "pi_error_on_retrieve"
        mock_retrieve.side_effect = stripe.error.StripeError("Error retrieving intent")

        response = self.client.post(
            self.base_url,
            json.dumps({"payment_intent_id": payment_intent_id}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 500)
        self.assertIn("Error retrieving intent", response.json()["error"])
