# inventory/tests/test_utils/test_create_update_sales_payment_intent.py

from django.test import TestCase
from unittest.mock import patch, MagicMock
from decimal import Decimal
import uuid
import stripe

# Import the function to be tested
from inventory.utils.create_update_sales_payment_intent import create_or_update_sales_payment_intent

# Import your models and factories
from payments.models import Payment
from inventory.models import TempSalesBooking, SalesProfile
from ..test_helpers.model_factories import (
    MotorcycleFactory,
    SalesProfileFactory,
    TempSalesBookingFactory,
    PaymentFactory,
)


class CreateUpdateSalesPaymentIntentTest(TestCase):
    """
    Tests for the create_or_update_sales_payment_intent utility function.
    Mocks Stripe API calls to prevent actual network requests.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up common test data for all tests.
        """
        cls.motorcycle = MotorcycleFactory()
        cls.sales_profile = SalesProfileFactory()

    @patch('stripe.PaymentIntent.create')
    @patch('stripe.PaymentIntent.retrieve')
    @patch('stripe.PaymentIntent.modify')
    def test_create_new_payment_intent(self, mock_modify, mock_retrieve, mock_create):
        """
        Test the creation of a new Stripe Payment Intent and Django Payment object.
        """
        # Mock the Stripe API response for creation
        mock_create.return_value = MagicMock(
            id=f"pi_{uuid.uuid4().hex}",
            amount=10000,
            currency='aud',
            status='requires_payment_method',
            metadata={'temp_sales_booking_uuid': str(uuid.uuid4()), 'sales_profile_id': str(self.sales_profile.id), 'booking_type': 'sales_booking'},
            description="Deposit for Motorcycle: 2023 Brand Model (Ref: TSB-ABCDEFGH)"
        )
        mock_retrieve.side_effect = Exception("Should not be called") # Ensure retrieve is not called
        mock_modify.side_effect = Exception("Should not be called")  # Ensure modify is not called

        temp_booking = TempSalesBookingFactory(
            motorcycle=self.motorcycle,
            sales_profile=self.sales_profile,
            amount_paid=Decimal('0.00'), # No prior payment
            stripe_payment_intent_id=None # No prior PI
        )
        amount_to_pay = Decimal('100.00')
        currency = 'AUD'

        stripe_intent, django_payment = create_or_update_sales_payment_intent(
            temp_booking,
            self.sales_profile,
            amount_to_pay,
            currency,
            existing_payment_obj=None # No existing payment object
        )

        # Assertions for Stripe API call
        mock_create.assert_called_once()
        self.assertEqual(mock_create.call_args[1]['amount'], 10000)
        self.assertEqual(mock_create.call_args[1]['currency'], 'AUD')
        self.assertIn('Deposit for Motorcycle', mock_create.call_args[1]['description'])
        self.assertEqual(mock_create.call_args[1]['metadata']['temp_sales_booking_uuid'], str(temp_booking.session_uuid))
        self.assertEqual(mock_create.call_args[1]['metadata']['sales_profile_id'], str(self.sales_profile.id))
        self.assertEqual(mock_create.call_args[1]['metadata']['booking_type'], 'sales_booking')


        # Assertions for Django Payment object
        self.assertIsNotNone(django_payment)
        self.assertIsInstance(django_payment, Payment)
        self.assertEqual(django_payment.temp_sales_booking, temp_booking)
        self.assertEqual(django_payment.sales_customer_profile, self.sales_profile)
        self.assertEqual(django_payment.stripe_payment_intent_id, stripe_intent.id)
        self.assertEqual(django_payment.amount, amount_to_pay)
        self.assertEqual(django_payment.currency, currency)
        self.assertEqual(django_payment.status, 'requires_payment_method')
        self.assertEqual(django_payment.description, mock_create.call_args[1]['description'])

    @patch('stripe.PaymentIntent.create')
    @patch('stripe.PaymentIntent.retrieve')
    @patch('stripe.PaymentIntent.modify')
    def test_update_existing_payment_intent_amount_currency_change(self, mock_modify, mock_retrieve, mock_create):
        """
        Test updating an existing Stripe Payment Intent when amount or currency changes.
        """
        existing_pi_id = f"pi_existing_{uuid.uuid4().hex}"
        initial_amount = Decimal('50.00')
        initial_currency = 'AUD'

        # Create a Django Payment object that will be passed as existing_payment_obj
        existing_payment_obj = PaymentFactory(
            stripe_payment_intent_id=existing_pi_id,
            amount=initial_amount,
            currency=initial_currency,
            status='requires_action', # Modifiable status
            temp_sales_booking=TempSalesBookingFactory(),
            sales_customer_profile=self.sales_profile
        )

        # Mock initial retrieval of the Payment Intent
        mock_retrieve.return_value = MagicMock(
            id=existing_pi_id,
            amount=int(initial_amount * 100),
            currency=initial_currency.lower(),
            status='requires_action'
        )

        # Mock the modification of the Payment Intent
        new_amount = Decimal('150.00')
        new_currency = 'USD'
        mock_modify.return_value = MagicMock(
            id=existing_pi_id,
            amount=int(new_amount * 100),
            currency=new_currency.lower(),
            status='requires_confirmation',
            metadata={'temp_sales_booking_uuid': str(existing_payment_obj.temp_sales_booking.session_uuid), 'sales_profile_id': str(self.sales_profile.id), 'booking_type': 'sales_booking'},
            description="Deposit for Motorcycle: 2023 Brand Model (Ref: TSB-ABCDEFGH)"
        )
        mock_create.side_effect = Exception("Should not be called") # Ensure create is not called

        temp_booking = existing_payment_obj.temp_sales_booking
        amount_to_pay = new_amount
        currency = new_currency

        stripe_intent, django_payment = create_or_update_sales_payment_intent(
            temp_booking,
            self.sales_profile,
            amount_to_pay,
            currency,
            existing_payment_obj=existing_payment_obj
        )

        # Assertions for Stripe API calls
        mock_retrieve.assert_called_once_with(existing_pi_id)
        mock_modify.assert_called_once()
        self.assertEqual(mock_modify.call_args[0][0], existing_pi_id) # First arg is the PI ID
        self.assertEqual(mock_modify.call_args[1]['amount'], int(new_amount * 100))
        self.assertEqual(mock_modify.call_args[1]['currency'], new_currency)
        self.assertEqual(mock_modify.call_args[1]['metadata']['sales_profile_id'], str(self.sales_profile.id))

        # Assertions for Django Payment object
        self.assertIsNotNone(django_payment)
        self.assertEqual(django_payment.id, existing_payment_obj.id) # Should be the same object
        self.assertEqual(django_payment.amount, new_amount)
        self.assertEqual(django_payment.currency, new_currency)
        self.assertEqual(django_payment.status, 'requires_confirmation')
        # Refresh from DB to ensure it was saved
        django_payment.refresh_from_db()
        self.assertEqual(django_payment.amount, new_amount)
        self.assertEqual(django_payment.currency, new_currency)
        self.assertEqual(django_payment.status, 'requires_confirmation')


    @patch('stripe.PaymentIntent.create')
    @patch('stripe.PaymentIntent.retrieve')
    @patch('stripe.PaymentIntent.modify')
    def test_update_existing_payment_intent_no_change(self, mock_modify, mock_retrieve, mock_create):
        """
        Test updating an existing Stripe Payment Intent when no amount/currency change.
        Only Django Payment object status should be updated if Stripe status differs.
        """
        existing_pi_id = f"pi_no_change_{uuid.uuid4().hex}"
        current_amount = Decimal('100.00')
        current_currency = 'AUD'

        # Create a Django Payment object that will be passed as existing_payment_obj
        existing_payment_obj = PaymentFactory(
            stripe_payment_intent_id=existing_pi_id,
            amount=current_amount,
            currency=current_currency,
            status='requires_action', # Current status in DB
            temp_sales_booking=TempSalesBookingFactory(),
            sales_customer_profile=self.sales_profile
        )

        # Mock initial retrieval of the Payment Intent from Stripe (same status as DB)
        mock_retrieve.return_value = MagicMock(
            id=existing_pi_id,
            amount=int(current_amount * 100),
            currency=current_currency.lower(),
            status='requires_action' # Same status as DB
        )
        mock_modify.side_effect = Exception("Should not be called")  # Ensure modify is not called
        mock_create.side_effect = Exception("Should not be called")  # Ensure create is not called

        temp_booking = existing_payment_obj.temp_sales_booking
        amount_to_pay = current_amount
        currency = current_currency

        stripe_intent, django_payment = create_or_update_sales_payment_intent(
            temp_booking,
            self.sales_profile,
            amount_to_pay,
            currency,
            existing_payment_obj=existing_payment_obj
        )

        # Assertions
        mock_retrieve.assert_called_once_with(existing_pi_id)
        mock_modify.assert_not_called()
        mock_create.assert_not_called()

        self.assertIsNotNone(django_payment)
        self.assertEqual(django_payment.id, existing_payment_obj.id)
        self.assertEqual(django_payment.amount, current_amount)
        self.assertEqual(django_payment.currency, current_currency)
        self.assertEqual(django_payment.status, 'requires_action') # Status should remain the same
        django_payment.refresh_from_db()
        self.assertEqual(django_payment.status, 'requires_action')

        # Test case where Stripe status changes, but amount/currency don't
        existing_payment_obj.status = 'requires_payment_method' # Simulate old status in DB
        existing_payment_obj.save()

        mock_retrieve.return_value = MagicMock(
            id=existing_pi_id,
            amount=int(current_amount * 100),
            currency=current_currency.lower(),
            status='succeeded' # Stripe PI is now succeeded
        )

        stripe_intent, django_payment = create_or_update_sales_payment_intent(
            temp_booking,
            self.sales_profile,
            amount_to_pay,
            currency,
            existing_payment_obj=existing_payment_obj
        )
        self.assertEqual(django_payment.status, 'succeeded') # Django payment should reflect new Stripe status
        django_payment.refresh_from_db()
        self.assertEqual(django_payment.status, 'succeeded')


    @patch('stripe.PaymentIntent.create')
    @patch('stripe.PaymentIntent.retrieve', side_effect=stripe.error.StripeError("No such payment_intent"))
    @patch('stripe.PaymentIntent.modify')
    def test_retrieve_failure_creates_new_intent(self, mock_modify, mock_retrieve, mock_create):
        """
        Test that if retrieving an existing Payment Intent fails (e.g., not found),
        a new one is created.
        """
        existing_pi_id = f"pi_retrieve_fail_{uuid.uuid4().hex}"
        amount_to_pay = Decimal('200.00')
        currency = 'AUD'

        existing_payment_obj = PaymentFactory(
            stripe_payment_intent_id=existing_pi_id,
            amount=Decimal('100.00'), # Old amount
            currency='AUD',
            status='requires_payment_method',
            temp_sales_booking=TempSalesBookingFactory(),
            sales_customer_profile=self.sales_profile
        )

        mock_create.return_value = MagicMock(
            id=f"pi_new_{uuid.uuid4().hex}",
            amount=int(amount_to_pay * 100),
            currency='aud',
            status='requires_payment_method'
        )
        mock_modify.side_effect = Exception("Should not be called")

        temp_booking = existing_payment_obj.temp_sales_booking

        stripe_intent, django_payment = create_or_update_sales_payment_intent(
            temp_booking,
            self.sales_profile,
            amount_to_pay,
            currency,
            existing_payment_obj=existing_payment_obj
        )

        # Assertions
        mock_retrieve.assert_called_once_with(existing_pi_id)
        mock_create.assert_called_once() # A new one should be created
        mock_modify.assert_not_called()

        self.assertIsNotNone(django_payment)
        self.assertNotEqual(django_payment.id, existing_payment_obj.id) # Should be a new Django Payment object instance if not updated by reference
        self.assertEqual(django_payment.stripe_payment_intent_id, stripe_intent.id)
        self.assertEqual(django_payment.amount, amount_to_pay)
        self.assertEqual(django_payment.currency, currency)


    @patch('stripe.PaymentIntent.create')
    @patch('stripe.PaymentIntent.retrieve')
    @patch('stripe.PaymentIntent.modify')
    def test_failed_intent_creates_new_intent(self, mock_modify, mock_retrieve, mock_create):
        """
        Test that if an existing Payment Intent has a 'failed' status, a new one is created.
        """
        existing_pi_id = f"pi_failed_{uuid.uuid4().hex}"
        current_amount = Decimal('100.00')
        current_currency = 'AUD'

        existing_payment_obj = PaymentFactory(
            stripe_payment_intent_id=existing_pi_id,
            amount=current_amount,
            currency=current_currency,
            status='failed', # Existing PI status is 'failed'
            temp_sales_booking=TempSalesBookingFactory(),
            sales_customer_profile=self.sales_profile
        )

        mock_retrieve.return_value = MagicMock(
            id=existing_pi_id,
            amount=int(current_amount * 100),
            currency=current_currency.lower(),
            status='failed'
        )
        mock_create.return_value = MagicMock(
            id=f"pi_new_failed_{uuid.uuid4().hex}",
            amount=int(current_amount * 100),
            currency='aud',
            status='requires_payment_method'
        )
        mock_modify.side_effect = Exception("Should not be called")

        temp_booking = existing_payment_obj.temp_sales_booking
        amount_to_pay = current_amount
        currency = current_currency

        stripe_intent, django_payment = create_or_update_sales_payment_intent(
            temp_booking,
            self.sales_profile,
            amount_to_pay,
            currency,
            existing_payment_obj=existing_payment_obj
        )

        # Assertions
        mock_retrieve.assert_called_once_with(existing_pi_id)
        mock_create.assert_called_once() # A new one should be created
        mock_modify.assert_not_called()

        self.assertIsNotNone(django_payment)
        self.assertNotEqual(django_payment.stripe_payment_intent_id, existing_pi_id) # Should be a new PI ID
        self.assertEqual(django_payment.stripe_payment_intent_id, stripe_intent.id)
        self.assertEqual(django_payment.status, 'requires_payment_method')

    @patch('stripe.PaymentIntent.create')
    @patch('stripe.PaymentIntent.retrieve')
    @patch('stripe.PaymentIntent.modify')
    def test_non_modifiable_and_non_succeeded_intent_creates_new_intent(self, mock_modify, mock_retrieve, mock_create):
        """
        Test that if an existing Payment Intent is not modifiable (e.g., 'succeeded')
        and not in 'succeeded' status, a new one is created.
        This scenario might be rare, but covers the logic.
        """
        existing_pi_id = f"pi_non_mod_non_succ_{uuid.uuid4().hex}"
        current_amount = Decimal('100.00')
        current_currency = 'AUD'

        existing_payment_obj = PaymentFactory(
            stripe_payment_intent_id=existing_pi_id,
            amount=current_amount,
            currency=current_currency,
            status='canceled', # A status that is usually not modifiable and not 'succeeded'
            temp_sales_booking=TempSalesBookingFactory(),
            sales_customer_profile=self.sales_profile
        )

        mock_retrieve.return_value = MagicMock(
            id=existing_pi_id,
            amount=int(current_amount * 100),
            currency=current_currency.lower(),
            status='canceled'
        )
        mock_create.return_value = MagicMock(
            id=f"pi_new_canceled_{uuid.uuid4().hex}",
            amount=int(current_amount * 100),
            currency='aud',
            status='requires_payment_method'
        )
        mock_modify.side_effect = Exception("Should not be called")

        temp_booking = existing_payment_obj.temp_sales_booking
        amount_to_pay = current_amount
        currency = current_currency

        stripe_intent, django_payment = create_or_update_sales_payment_intent(
            temp_booking,
            self.sales_profile,
            amount_to_pay,
            currency,
            existing_payment_obj=existing_payment_obj
        )

        # Assertions
        mock_retrieve.assert_called_once_with(existing_pi_id)
        mock_create.assert_called_once() # A new one should be created
        mock_modify.assert_not_called()

        self.assertIsNotNone(django_payment)
        self.assertNotEqual(django_payment.stripe_payment_intent_id, existing_pi_id) # Should be a new PI ID
        self.assertEqual(django_payment.stripe_payment_intent_id, stripe_intent.id)
        self.assertEqual(django_payment.status, 'requires_payment_method')


    @patch('stripe.PaymentIntent.create')
    @patch('stripe.PaymentIntent.retrieve')
    @patch('stripe.PaymentIntent.modify')
    def test_metadata_and_description(self, mock_modify, mock_retrieve, mock_create):
        """
        Verify that correct metadata and description are passed to Stripe API calls.
        """
        temp_booking = TempSalesBookingFactory(
            motorcycle=self.motorcycle,
            sales_profile=self.sales_profile,
            amount_paid=Decimal('0.00'),
            stripe_payment_intent_id=None
        )
        amount_to_pay = Decimal('75.00')
        currency = 'EUR'

        mock_create.return_value = MagicMock(
            id=f"pi_meta_{uuid.uuid4().hex}",
            amount=int(amount_to_pay * 100),
            currency='eur',
            status='requires_payment_method',
            metadata={'temp_sales_booking_uuid': str(temp_booking.session_uuid), 'sales_profile_id': str(self.sales_profile.id), 'booking_type': 'sales_booking'},
            description=f"Deposit for Motorcycle: {self.motorcycle.year} {self.motorcycle.brand} {self.motorcycle.model}"
        )
        mock_retrieve.side_effect = Exception("Should not be called")
        mock_modify.side_effect = Exception("Should not be called")

        stripe_intent, django_payment = create_or_update_sales_payment_intent(
            temp_booking,
            self.sales_profile,
            amount_to_pay,
            currency,
            existing_payment_obj=None
        )

        # Check create call arguments
        create_args, create_kwargs = mock_create.call_args
        self.assertEqual(create_kwargs['amount'], int(amount_to_pay * 100))
        self.assertEqual(create_kwargs['currency'], currency)
        self.assertEqual(create_kwargs['metadata']['temp_sales_booking_uuid'], str(temp_booking.session_uuid))
        self.assertEqual(create_kwargs['metadata']['sales_profile_id'], str(self.sales_profile.id))
        self.assertEqual(create_kwargs['metadata']['booking_type'], 'sales_booking')
        expected_description = (
            f"Deposit for Motorcycle: {self.motorcycle.year} "
            f"{self.motorcycle.brand} {self.motorcycle.model} "
        )
        self.assertEqual(create_kwargs['description'], expected_description)

    @patch('stripe.PaymentIntent.create')
    @patch('stripe.PaymentIntent.retrieve')
    @patch('stripe.PaymentIntent.modify')
    def test_sales_profile_association(self, mock_modify, mock_retrieve, mock_create):
        """
        Verify that the sales_customer_profile is correctly associated with the Payment object.
        """
        temp_booking = TempSalesBookingFactory(
            motorcycle=self.motorcycle,
            sales_profile=self.sales_profile,
            amount_paid=Decimal('0.00'),
            stripe_payment_intent_id=None
        )
        amount_to_pay = Decimal('120.00')
        currency = 'AUD'

        mock_create.return_value = MagicMock(
            id=f"pi_assoc_{uuid.uuid4().hex}",
            amount=int(amount_to_pay * 100),
            currency='aud',
            status='requires_payment_method',
            metadata={}, # Not testing metadata here
            description=""
        )
        mock_retrieve.side_effect = Exception("Should not be called")
        mock_modify.side_effect = Exception("Should not be called")

        stripe_intent, django_payment = create_or_update_sales_payment_intent(
            temp_booking,
            self.sales_profile, # Pass the sales profile
            amount_to_pay,
            currency,
            existing_payment_obj=None
        )

        self.assertIsNotNone(django_payment.sales_customer_profile)
        self.assertEqual(django_payment.sales_customer_profile, self.sales_profile)

        # Test updating an existing payment object with no sales_customer_profile initially
        existing_payment_obj_no_profile = PaymentFactory(
            stripe_payment_intent_id=f"pi_no_profile_{uuid.uuid4().hex}",
            amount=Decimal('50.00'),
            currency='AUD',
            status='requires_action',
            temp_sales_booking=temp_booking,
            sales_customer_profile=None # Initially no profile
        )

        mock_retrieve.return_value = MagicMock(
            id=existing_payment_obj_no_profile.stripe_payment_intent_id,
            amount=int(amount_to_pay * 100),
            currency='aud',
            status='requires_confirmation'
        )
        mock_modify.return_value = mock_retrieve.return_value # Modify returns the same mock

        stripe_intent_updated, django_payment_updated = create_or_update_sales_payment_intent(
            temp_booking,
            self.sales_profile, # Pass the sales profile during update
            amount_to_pay,
            currency,
            existing_payment_obj=existing_payment_obj_no_profile
        )

        self.assertIsNotNone(django_payment_updated.sales_customer_profile)
        self.assertEqual(django_payment_updated.sales_customer_profile, self.sales_profile)
        django_payment_updated.refresh_from_db()
        self.assertEqual(django_payment_updated.sales_customer_profile, self.sales_profile)

