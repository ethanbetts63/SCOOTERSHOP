from django.test import TestCase
from unittest.mock import patch, MagicMock
from decimal import Decimal
import uuid
import stripe

from inventory.utils.create_update_sales_payment_intent import (
    create_or_update_sales_payment_intent,
)

from payments.models import Payment

from inventory.tests.test_helpers.model_factories import TempSalesBookingFactory, SalesProfileFactory, MotorcycleFactory
from payments.tests.test_helpers.model_factories import PaymentFactory



class CreateUpdateSalesPaymentIntentTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.motorcycle = MotorcycleFactory()
        cls.sales_profile = SalesProfileFactory()

    @patch("stripe.PaymentIntent.create")
    @patch("stripe.PaymentIntent.retrieve")
    @patch("stripe.PaymentIntent.modify")
    def test_create_new_payment_intent(self, mock_modify, mock_retrieve, mock_create):
        mock_create.return_value = MagicMock(
            id=f"pi_{uuid.uuid4().hex}",
            amount=10000,
            currency="aud",
            status="requires_payment_method",
            metadata={
                "temp_sales_booking_uuid": str(uuid.uuid4()),
                "sales_profile_id": str(self.sales_profile.id),
                "booking_type": "sales_booking",
            },
            description="Deposit for Motorcycle: 2023 Brand Model (Ref: TSB-ABCDEFGH)",
        )
        mock_retrieve.side_effect = Exception("Should not be called")
        mock_modify.side_effect = Exception("Should not be called")

        temp_booking = TempSalesBookingFactory(
            motorcycle=self.motorcycle,
            sales_profile=self.sales_profile,
            amount_paid=Decimal("0.00"),
            stripe_payment_intent_id=None,
        )
        amount_to_pay = Decimal("100.00")
        currency = "AUD"

        stripe_intent, django_payment = create_or_update_sales_payment_intent(
            temp_booking,
            self.sales_profile,
            amount_to_pay,
            currency,
            existing_payment_obj=None,
        )

        mock_create.assert_called_once()
        self.assertEqual(mock_create.call_args[1]["amount"], 10000)
        self.assertEqual(mock_create.call_args[1]["currency"], "AUD")
        self.assertIn("Deposit for Motorcycle", mock_create.call_args[1]["description"])
        self.assertEqual(
            mock_create.call_args[1]["metadata"]["temp_sales_booking_uuid"],
            str(temp_booking.session_uuid),
        )
        self.assertEqual(
            mock_create.call_args[1]["metadata"]["sales_profile_id"],
            str(self.sales_profile.id),
        )
        self.assertEqual(
            mock_create.call_args[1]["metadata"]["booking_type"], "sales_booking"
        )

        self.assertIsNotNone(django_payment)
        self.assertIsInstance(django_payment, Payment)
        self.assertEqual(django_payment.temp_sales_booking, temp_booking)
        self.assertEqual(django_payment.sales_customer_profile, self.sales_profile)
        self.assertEqual(django_payment.stripe_payment_intent_id, stripe_intent.id)
        self.assertEqual(django_payment.amount, amount_to_pay)
        self.assertEqual(django_payment.currency, currency)
        self.assertEqual(django_payment.status, "requires_payment_method")
        self.assertEqual(
            django_payment.description, mock_create.call_args[1]["description"]
        )

    @patch("stripe.PaymentIntent.create")
    @patch("stripe.PaymentIntent.retrieve")
    @patch("stripe.PaymentIntent.modify")
    def test_update_existing_payment_intent_amount_currency_change(
        self, mock_modify, mock_retrieve, mock_create
    ):
        existing_pi_id = f"pi_existing_{uuid.uuid4().hex}"
        initial_amount = Decimal("50.00")
        initial_currency = "AUD"

        temp_booking_for_existing = TempSalesBookingFactory()
        existing_payment_obj = PaymentFactory(
            stripe_payment_intent_id=existing_pi_id,
            amount=initial_amount,
            currency=initial_currency,
            status="requires_action",
            temp_sales_booking=temp_booking_for_existing,
            sales_customer_profile=self.sales_profile,
        )

        mock_retrieve.return_value = MagicMock(
            id=existing_pi_id,
            amount=int(initial_amount * 100),
            currency=initial_currency.lower(),
            status="requires_action",
        )

        new_amount = Decimal("150.00")
        new_currency = "USD"
        mock_modify.return_value = MagicMock(
            id=existing_pi_id,
            amount=int(new_amount * 100),
            currency=new_currency.lower(),
            status="requires_confirmation",
            metadata={
                "temp_sales_booking_uuid": str(
                    existing_payment_obj.temp_sales_booking.session_uuid
                ),
                "sales_profile_id": str(self.sales_profile.id),
                "booking_type": "sales_booking",
            },
            description="Deposit for Motorcycle: 2023 Brand Model (Ref: TSB-ABCDEFGH)",
        )
        mock_create.side_effect = Exception("Should not be called")

        temp_booking = existing_payment_obj.temp_sales_booking
        amount_to_pay = new_amount
        currency = new_currency

        stripe_intent, django_payment = create_or_update_sales_payment_intent(
            temp_booking,
            self.sales_profile,
            amount_to_pay,
            currency,
            existing_payment_obj=existing_payment_obj,
        )

        mock_retrieve.assert_called_once_with(existing_pi_id)
        mock_modify.assert_called_once()
        self.assertEqual(mock_modify.call_args[0][0], existing_pi_id)
        self.assertEqual(mock_modify.call_args[1]["amount"], int(new_amount * 100))
        self.assertEqual(mock_modify.call_args[1]["currency"], new_currency)
        self.assertEqual(
            mock_modify.call_args[1]["metadata"]["sales_profile_id"],
            str(self.sales_profile.id),
        )

        self.assertIsNotNone(django_payment)
        self.assertEqual(django_payment.id, existing_payment_obj.id)
        self.assertEqual(django_payment.amount, new_amount)
        self.assertEqual(django_payment.currency, new_currency)
        self.assertEqual(django_payment.status, "requires_confirmation")
        django_payment.refresh_from_db()
        self.assertEqual(django_payment.amount, new_amount)
        self.assertEqual(django_payment.currency, new_currency)
        self.assertEqual(django_payment.status, "requires_confirmation")

    @patch("stripe.PaymentIntent.create")
    @patch("stripe.PaymentIntent.retrieve")
    @patch("stripe.PaymentIntent.modify")
    def test_update_existing_payment_intent_no_change(
        self, mock_modify, mock_retrieve, mock_create
    ):
        existing_pi_id = f"pi_no_change_{uuid.uuid4().hex}"
        current_amount = Decimal("100.00")
        current_currency = "AUD"

        temp_booking_for_existing = TempSalesBookingFactory()
        existing_payment_obj = PaymentFactory(
            stripe_payment_intent_id=existing_pi_id,
            amount=current_amount,
            currency=current_currency,
            status="requires_action",
            temp_sales_booking=temp_booking_for_existing,
            sales_customer_profile=self.sales_profile,
        )

        mock_retrieve.return_value = MagicMock(
            id=existing_pi_id,
            amount=int(current_amount * 100),
            currency=current_currency.lower(),
            status="requires_action",
        )
        mock_modify.side_effect = Exception("Should not be called")
        mock_create.side_effect = Exception("Should not be called")

        temp_booking = existing_payment_obj.temp_sales_booking
        amount_to_pay = current_amount
        currency = current_currency

        stripe_intent, django_payment = create_or_update_sales_payment_intent(
            temp_booking,
            self.sales_profile,
            amount_to_pay,
            currency,
            existing_payment_obj=existing_payment_obj,
        )

        mock_retrieve.assert_called_once_with(existing_pi_id)
        mock_modify.assert_not_called()
        mock_create.assert_not_called()

        self.assertIsNotNone(django_payment)
        self.assertEqual(django_payment.id, existing_payment_obj.id)
        self.assertEqual(django_payment.amount, current_amount)
        self.assertEqual(django_payment.currency, current_currency)
        self.assertEqual(django_payment.status, "requires_action")
        django_payment.refresh_from_db()
        self.assertEqual(django_payment.status, "requires_action")

        existing_payment_obj.status = "requires_payment_method"
        existing_payment_obj.save()

        mock_retrieve.reset_mock(side_effect=True)
        mock_modify.reset_mock(side_effect=True)
        mock_create.reset_mock(side_effect=True)

        mock_retrieve.return_value = MagicMock(
            id=existing_pi_id,
            amount=int(current_amount * 100),
            currency=current_currency.lower(),
            status="succeeded",
        )

        stripe_intent, django_payment = create_or_update_sales_payment_intent(
            temp_booking,
            self.sales_profile,
            amount_to_pay,
            currency,
            existing_payment_obj=existing_payment_obj,
        )
        self.assertEqual(django_payment.status, "succeeded")
        django_payment.refresh_from_db()
        self.assertEqual(django_payment.status, "succeeded")

    @patch("stripe.PaymentIntent.create")
    @patch(
        "stripe.PaymentIntent.retrieve",
        side_effect=stripe.error.StripeError("No such payment_intent"),
    )
    @patch("stripe.PaymentIntent.modify")
    def test_retrieve_failure_creates_new_intent(
        self, mock_modify, mock_retrieve, mock_create
    ):
        existing_pi_id = f"pi_retrieve_fail_{uuid.uuid4().hex}"
        amount_to_pay = Decimal("200.00")
        currency = "AUD"

        temp_booking_for_existing_payment = TempSalesBookingFactory()
        existing_payment_obj = PaymentFactory(
            stripe_payment_intent_id=existing_pi_id,
            amount=Decimal("100.00"),
            currency="AUD",
            status="requires_payment_method",
            temp_sales_booking=temp_booking_for_existing_payment,
            sales_customer_profile=self.sales_profile,
        )

        mock_create.return_value = MagicMock(
            id=f"pi_new_{uuid.uuid4().hex}",
            amount=int(amount_to_pay * 100),
            currency="aud",
            status="requires_payment_method",
        )
        mock_modify.side_effect = Exception("Should not be called")

        new_temp_booking_for_new_payment = TempSalesBookingFactory()

        stripe_intent, django_payment = create_or_update_sales_payment_intent(
            new_temp_booking_for_new_payment,
            self.sales_profile,
            amount_to_pay,
            currency,
            existing_payment_obj=existing_payment_obj,
        )

        mock_retrieve.assert_called_once_with(existing_pi_id)
        mock_create.assert_called_once()
        mock_modify.assert_not_called()

        self.assertIsNotNone(django_payment)
        self.assertNotEqual(django_payment.id, existing_payment_obj.id)
        self.assertEqual(django_payment.stripe_payment_intent_id, stripe_intent.id)
        self.assertEqual(django_payment.amount, amount_to_pay)
        self.assertEqual(django_payment.currency, currency)
        self.assertEqual(
            django_payment.temp_sales_booking, new_temp_booking_for_new_payment
        )

    @patch("stripe.PaymentIntent.create")
    @patch("stripe.PaymentIntent.retrieve")
    @patch("stripe.PaymentIntent.modify")
    def test_failed_intent_creates_new_intent(
        self, mock_modify, mock_retrieve, mock_create
    ):
        existing_pi_id = f"pi_failed_{uuid.uuid4().hex}"
        current_amount = Decimal("100.00")
        current_currency = "AUD"

        temp_booking_for_existing_payment = TempSalesBookingFactory()
        existing_payment_obj = PaymentFactory(
            stripe_payment_intent_id=existing_pi_id,
            amount=current_amount,
            currency=current_currency,
            status="failed",
            temp_sales_booking=temp_booking_for_existing_payment,
            sales_customer_profile=self.sales_profile,
        )

        mock_retrieve.return_value = MagicMock(
            id=existing_pi_id,
            amount=int(current_amount * 100),
            currency=current_currency.lower(),
            status="failed",
        )
        mock_create.return_value = MagicMock(
            id=f"pi_new_failed_{uuid.uuid4().hex}",
            amount=int(current_amount * 100),
            currency="aud",
            status="requires_payment_method",
        )
        mock_modify.side_effect = Exception("Should not be called")

        new_temp_booking_for_new_payment = TempSalesBookingFactory()

        stripe_intent, django_payment = create_or_update_sales_payment_intent(
            new_temp_booking_for_new_payment,
            self.sales_profile,
            amount_to_pay=current_amount,
            currency=current_currency,
            existing_payment_obj=existing_payment_obj,
        )

        mock_retrieve.assert_called_once_with(existing_pi_id)
        mock_create.assert_called_once()
        mock_modify.assert_not_called()

        self.assertIsNotNone(django_payment)
        self.assertNotEqual(django_payment.stripe_payment_intent_id, existing_pi_id)
        self.assertEqual(django_payment.stripe_payment_intent_id, stripe_intent.id)
        self.assertEqual(django_payment.status, "requires_payment_method")
        self.assertEqual(
            django_payment.temp_sales_booking, new_temp_booking_for_new_payment
        )

    @patch("stripe.PaymentIntent.create")
    @patch("stripe.PaymentIntent.retrieve")
    @patch("stripe.PaymentIntent.modify")
    def test_non_modifiable_and_non_succeeded_intent_creates_new_intent(
        self, mock_modify, mock_retrieve, mock_create
    ):
        existing_pi_id = f"pi_non_mod_non_succ_{uuid.uuid4().hex}"
        current_amount = Decimal("100.00")
        current_currency = "AUD"

        temp_booking_for_existing_payment = TempSalesBookingFactory()
        existing_payment_obj = PaymentFactory(
            stripe_payment_intent_id=existing_pi_id,
            amount=current_amount,
            currency=current_currency,
            status="canceled",
            temp_sales_booking=temp_booking_for_existing_payment,
            sales_customer_profile=self.sales_profile,
        )

        mock_retrieve.return_value = MagicMock(
            id=existing_pi_id,
            amount=int(current_amount * 100),
            currency=current_currency.lower(),
            status="canceled",
        )
        mock_create.return_value = MagicMock(
            id=f"pi_new_canceled_{uuid.uuid4().hex}",
            amount=int(current_amount * 100),
            currency="aud",
            status="requires_payment_method",
        )
        mock_modify.side_effect = Exception("Should not be called")

        new_temp_booking_for_new_payment = TempSalesBookingFactory()

        stripe_intent, django_payment = create_or_update_sales_payment_intent(
            new_temp_booking_for_new_payment,
            self.sales_profile,
            amount_to_pay=current_amount,
            currency=current_currency,
            existing_payment_obj=existing_payment_obj,
        )

        mock_retrieve.assert_called_once_with(existing_pi_id)
        mock_create.assert_called_once()
        mock_modify.assert_not_called()

        self.assertIsNotNone(django_payment)
        self.assertNotEqual(django_payment.stripe_payment_intent_id, existing_pi_id)
        self.assertEqual(django_payment.stripe_payment_intent_id, stripe_intent.id)
        self.assertEqual(django_payment.status, "requires_payment_method")
        self.assertEqual(
            django_payment.temp_sales_booking, new_temp_booking_for_new_payment
        )

    @patch("stripe.PaymentIntent.create")
    @patch("stripe.PaymentIntent.retrieve")
    @patch("stripe.PaymentIntent.modify")
    def test_metadata_and_description(self, mock_modify, mock_retrieve, mock_create):
        temp_booking = TempSalesBookingFactory(
            motorcycle=self.motorcycle,
            sales_profile=self.sales_profile,
            amount_paid=Decimal("0.00"),
            stripe_payment_intent_id=None,
        )
        amount_to_pay = Decimal("75.00")
        currency = "EUR"

        mock_create.return_value = MagicMock(
            id=f"pi_meta_{uuid.uuid4().hex}",
            amount=int(amount_to_pay * 100),
            currency="eur",
            status="requires_payment_method",
            metadata={
                "temp_sales_booking_uuid": str(temp_booking.session_uuid),
                "sales_profile_id": str(self.sales_profile.id),
                "booking_type": "sales_booking",
            },
            description=f"Deposit for Motorcycle: {self.motorcycle.year} {self.motorcycle.brand} {self.motorcycle.model} (Ref: {temp_booking.session_uuid})",
        )
        mock_retrieve.side_effect = Exception("Should not be called")
        mock_modify.side_effect = Exception("Should not be called")

        stripe_intent, django_payment = create_or_update_sales_payment_intent(
            temp_booking,
            self.sales_profile,
            amount_to_pay,
            currency,
            existing_payment_obj=None,
        )

        create_args, create_kwargs = mock_create.call_args
        self.assertEqual(create_kwargs["amount"], int(amount_to_pay * 100))
        self.assertEqual(create_kwargs["currency"], currency)
        self.assertEqual(
            create_kwargs["metadata"]["temp_sales_booking_uuid"],
            str(temp_booking.session_uuid),
        )
        self.assertEqual(
            create_kwargs["metadata"]["sales_profile_id"], str(self.sales_profile.id)
        )
        self.assertEqual(create_kwargs["metadata"]["booking_type"], "sales_booking")
        expected_description = (
            f"Deposit for Motorcycle: {self.motorcycle.year} "
            f"{self.motorcycle.brand} {self.motorcycle.model} "
            f"(Ref: {temp_booking.session_uuid})"
        )
        self.assertEqual(create_kwargs["description"], expected_description)

    @patch("stripe.PaymentIntent.create")
    @patch("stripe.PaymentIntent.retrieve")
    @patch("stripe.PaymentIntent.modify")
    def test_sales_profile_association(self, mock_modify, mock_retrieve, mock_create):
        temp_booking_for_new_payment = TempSalesBookingFactory(
            motorcycle=self.motorcycle,
            sales_profile=self.sales_profile,
            amount_paid=Decimal("0.00"),
            stripe_payment_intent_id=None,
        )
        amount_to_pay_new = Decimal("120.00")
        currency_new = "AUD"

        mock_create.reset_mock(side_effect=True)
        mock_retrieve.reset_mock(side_effect=True)
        mock_modify.reset_mock(side_effect=True)
        mock_retrieve.side_effect = Exception("Should not be called for new creation")
        mock_modify.side_effect = Exception("Should not be called for new creation")

        mock_create.return_value = MagicMock(
            id=f"pi_assoc_new_{uuid.uuid4().hex}",
            amount=int(amount_to_pay_new * 100),
            currency="aud",
            status="requires_payment_method",
            metadata={},
            description="",
        )

        stripe_intent_new, django_payment_new = create_or_update_sales_payment_intent(
            temp_booking_for_new_payment,
            self.sales_profile,
            amount_to_pay_new,
            currency_new,
            existing_payment_obj=None,
        )

        self.assertIsNotNone(django_payment_new.sales_customer_profile)
        self.assertEqual(django_payment_new.sales_customer_profile, self.sales_profile)
        self.assertEqual(
            django_payment_new.temp_sales_booking, temp_booking_for_new_payment
        )

        temp_booking_for_update_scenario = TempSalesBookingFactory(
            motorcycle=self.motorcycle
        )
        existing_payment_obj_no_profile = PaymentFactory(
            stripe_payment_intent_id=f"pi_no_profile_{uuid.uuid4().hex}",
            amount=Decimal("50.00"),
            currency="AUD",
            status="requires_action",
            temp_sales_booking=temp_booking_for_update_scenario,
            sales_customer_profile=None,
        )

        mock_create.reset_mock(side_effect=True)
        mock_retrieve.reset_mock(side_effect=True)
        mock_modify.reset_mock(side_effect=True)
        mock_create.side_effect = Exception("Should not be called for update scenario")

        amount_to_pay_update = Decimal("150.00")
        currency_update = "AUD"

        mock_retrieve.return_value = MagicMock(
            id=existing_payment_obj_no_profile.stripe_payment_intent_id,
            amount=int(existing_payment_obj_no_profile.amount * 100),
            currency="aud",
            status="requires_action",
        )
        mock_modify.return_value = MagicMock(
            id=existing_payment_obj_no_profile.stripe_payment_intent_id,
            amount=int(amount_to_pay_update * 100),
            currency="aud",
            status="requires_confirmation",
        )

        stripe_intent_updated, django_payment_updated = (
            create_or_update_sales_payment_intent(
                temp_booking_for_update_scenario,
                self.sales_profile,
                amount_to_pay_update,
                currency_update,
                existing_payment_obj=existing_payment_obj_no_profile,
            )
        )

        self.assertIsNotNone(django_payment_updated.sales_customer_profile)
        self.assertEqual(
            django_payment_updated.sales_customer_profile, self.sales_profile
        )
        django_payment_updated.refresh_from_db()
        self.assertEqual(
            django_payment_updated.sales_customer_profile, self.sales_profile
        )
        self.assertEqual(django_payment_updated.amount, amount_to_pay_update)
        self.assertEqual(django_payment_updated.status, "requires_confirmation")
