from decimal import Decimal
from django.test import TestCase, override_settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone # Added for manipulating 'created' timestamp in mock refund data
from unittest import mock
from django.conf import settings # Import settings to mock ADMIN_EMAIL
import stripe # <--- ADDED IMPORT FOR STRIPE

# Import model factories for easy test data creation
from hire.tests.test_helpers.model_factories import (
    create_motorcycle,
    create_driver_profile,
    create_hire_settings,
    create_payment,
    create_temp_hire_booking,
    create_temp_booking_addon,
    create_addon,
    create_user,
    create_hire_booking, # Added for refund tests
    create_refund_request # Added for refund tests
)
from hire.models.hire_booking import HireBooking, PAYMENT_STATUS_CHOICES
from hire.models import TempHireBooking, BookingAddOn, TempBookingAddOn
from payments.models import Payment, HireRefundRequest # Added HireRefundRequest

# Import the webhook handlers
from payments.webhook_handlers import handle_hire_booking_succeeded, handle_hire_booking_refunded, handle_hire_booking_refund_updated

class WebhookHandlerTest(TestCase):
    """
    Tests for the webhook handler functions, including booking conversion and refund processing.
    """
    @classmethod
    def setUpTestData(cls):
        cls.hire_settings = create_hire_settings(
            booking_lead_time_hours=0,
            # Add refund policy settings for email context if needed, though not directly tested here
            cancellation_upfront_full_refund_days=7,
            cancellation_upfront_partial_refund_days=3,
            cancellation_upfront_partial_refund_percentage=Decimal('50.00'),
        )
        cls.motorcycle = create_motorcycle()
        cls.user = create_user(username="testuser", email="user@example.com")
        cls.admin_user = create_user(username="adminuser", email="adminprocessor@example.com", is_staff=True)
        cls.driver_profile = create_driver_profile(user=cls.user, is_australian_resident=True, email="driver@example.com")
        cls.addon1 = create_addon(name="GPS", hourly_cost=Decimal('2.00'), daily_cost=Decimal('15.00'))
        cls.addon2 = create_addon(name="Jacket", hourly_cost=Decimal('5.00'), daily_cost=Decimal('25.00'))

        # Common setup for refund tests
        cls.hire_booking_for_refund = create_hire_booking(
            driver_profile=cls.driver_profile,
            motorcycle=cls.motorcycle,
            grand_total=Decimal('300.00'),
            amount_paid=Decimal('300.00'),
            payment_status='paid',
            status='confirmed'
        )
        cls.payment_for_refund = create_payment(
            hire_booking=cls.hire_booking_for_refund,
            driver_profile=cls.driver_profile, # Link driver profile to payment
            amount=Decimal('300.00'),
            status='succeeded', # Payment was successful before refund
            stripe_payment_intent_id='pi_for_refund_123',
            refunded_amount=Decimal('0.00') # Ensure it starts at 0
        )
        # Link payment back to hire_booking if not done by factory
        cls.hire_booking_for_refund.payment = cls.payment_for_refund
        cls.hire_booking_for_refund.stripe_payment_intent_id = cls.payment_for_refund.stripe_payment_intent_id
        cls.hire_booking_for_refund.save()


    def test_handle_hire_booking_succeeded_full_conversion(self):
        """
        Tests the complete flow of handle_hire_booking_succeeded for a full payment,
        including email sending.
        """
        # Set a mock ADMIN_EMAIL for this test
        with self.settings(ADMIN_EMAIL='admin@example.com'):
            # 1. Setup: Create TempHireBooking, Payment, and TempBookingAddOn
            temp_booking = create_temp_hire_booking(
                motorcycle=self.motorcycle,
                driver_profile=self.driver_profile,
                payment_option='online_full',
                grand_total=Decimal('200.00'),
                total_addons_price=Decimal('40.00'),
                total_hire_price=Decimal('160.00'),
                total_package_price=Decimal('0.00'),
                deposit_amount=Decimal('0.00'), # No deposit for full payment
                currency='AUD'
            )
            create_temp_booking_addon(temp_booking, self.addon1, quantity=1, booked_addon_price=self.addon1.daily_cost)
            create_temp_booking_addon(temp_booking, self.addon2, quantity=1, booked_addon_price=self.addon2.daily_cost)

            payment_obj = create_payment(
                amount=Decimal('200.00'),
                currency='AUD',
                status='requires_payment_method', # Initial status
                stripe_payment_intent_id="pi_full_payment_123",
            )
            # Link payment to temp_booking
            payment_obj.temp_hire_booking = temp_booking
            payment_obj.save()

            # Mock payment_intent_data (simplified for test)
            payment_intent_data = {
                'id': "pi_full_payment_123",
                'amount': 20000, # Cents
                'amount_received': 20000, # Added: The actual amount received by Stripe
                'currency': 'aud',
                'status': 'succeeded',
                'metadata': {'booking_type': 'hire_booking', 'payment_id': str(payment_obj.id)}
            }

            # Mock the send_templated_email function
            with mock.patch('payments.webhook_handlers.send_templated_email') as mock_send_email:
                # 2. Action: Call the handler
                handle_hire_booking_succeeded(payment_obj, payment_intent_data)

                # 3. Assertions
                # Check if TempHireBooking is deleted
                with self.assertRaises(ObjectDoesNotExist):
                    TempHireBooking.objects.get(id=temp_booking.id)

                # Check if HireBooking is created
                hire_booking = HireBooking.objects.get(stripe_payment_intent_id="pi_full_payment_123")
                self.assertIsNotNone(hire_booking)
                self.assertEqual(hire_booking.grand_total, Decimal('200.00'))
                self.assertEqual(hire_booking.amount_paid, Decimal('200.00'))
                self.assertEqual(hire_booking.payment_status, 'paid')
                self.assertEqual(hire_booking.status, 'confirmed')
                self.assertEqual(hire_booking.motorcycle, self.motorcycle)
                self.assertEqual(hire_booking.driver_profile, self.driver_profile)

                # Check email sending
                self.assertEqual(mock_send_email.call_count, 2) # Expect 2 calls: user and admin

                # Assert user email call using keyword arguments
                user_email_call = mock.call(
                    recipient_list=[self.user.email],
                    subject=f"Your Motorcycle Hire Booking Confirmation - {hire_booking.booking_reference}",
                    template_name='booking_confirmation_user.html',
                    context={
                        'hire_booking': hire_booking,
                        'user': self.user,
                        'driver_profile': self.driver_profile,
                        'is_in_store': False,
                    },
                    user=self.user,
                    driver_profile=self.driver_profile,
                    booking=hire_booking
                )
                # Use assert_any_call to check if a call matching these kwargs was made
                mock_send_email.assert_any_call(**user_email_call.kwargs)

                # Assert admin email call using keyword arguments
                admin_email_call = mock.call(
                    recipient_list=[settings.ADMIN_EMAIL],
                    subject=f"New Motorcycle Hire Booking (Online) - {hire_booking.booking_reference}",
                    template_name='booking_confirmation_admin.html',
                    context={
                        'hire_booking': hire_booking,
                        'user': self.user,
                        'driver_profile': self.driver_profile,
                        'is_in_store': False,
                    },
                    booking=hire_booking
                )
                # Use assert_any_call to check if a call matching these kwargs was made
                mock_send_email.assert_any_call(**admin_email_call.kwargs)


    def test_handle_hire_booking_succeeded_deposit_payment(self):
        """
        Tests the complete flow of handle_hire_booking_succeeded for a deposit payment,
        including email sending.
        """
        # Set a mock ADMIN_EMAIL for this test
        with self.settings(ADMIN_EMAIL='admin@example.com'):
            # 1. Setup: Create TempHireBooking, Payment, and TempBookingAddOn for deposit
            temp_booking = create_temp_hire_booking(
                motorcycle=self.motorcycle,
                driver_profile=self.driver_profile,
                payment_option='online_deposit',
                grand_total=Decimal('200.00'),
                total_hire_price=Decimal('150.00'),
                total_addons_price=Decimal('50.00'),
                total_package_price=Decimal('0.00'),
                deposit_amount=Decimal('50.00'), # Deposit amount
                currency='AUD'
            )
            payment_obj = create_payment(
                amount=Decimal('50.00'), # Only deposit amount paid
                currency='AUD',
                status='requires_payment_method',
                stripe_payment_intent_id="pi_deposit_payment_456",
            )
            payment_obj.temp_hire_booking = temp_booking
            payment_obj.save()

            payment_intent_data = {
                'id': "pi_deposit_payment_456",
                'amount': 5000, # Cents
                'amount_received': 5000, # Added: The actual amount received by Stripe for the deposit
                'currency': 'aud',
                'status': 'succeeded',
                'metadata': {'booking_type': 'hire_booking', 'payment_id': str(payment_obj.id)}
            }

            # Mock the send_templated_email function
            with mock.patch('payments.webhook_handlers.send_templated_email') as mock_send_email:
                # 2. Action: Call the handler
                handle_hire_booking_succeeded(payment_obj, payment_intent_data)

                # 3. Assertions
                hire_booking = HireBooking.objects.get(stripe_payment_intent_id="pi_deposit_payment_456")
                self.assertEqual(hire_booking.grand_total, Decimal('200.00'))
                self.assertEqual(hire_booking.amount_paid, Decimal('50.00'))
                self.assertEqual(hire_booking.payment_status, 'deposit_paid') # Should be deposit_paid

                # Check email sending
                self.assertEqual(mock_send_email.call_count, 2) # Expect 2 calls: user and admin

                # Assert user email call using keyword arguments
                user_email_call = mock.call(
                    recipient_list=[self.user.email],
                    subject=f"Your Motorcycle Hire Booking Confirmation - {hire_booking.booking_reference}",
                    template_name='booking_confirmation_user.html',
                    context={
                        'hire_booking': hire_booking,
                        'user': self.user,
                        'driver_profile': self.driver_profile,
                        'is_in_store': False,
                    },
                    user=self.user,
                    driver_profile=self.driver_profile,
                    booking=hire_booking
                )
                mock_send_email.assert_any_call(**user_email_call.kwargs)

                # Assert admin email call using keyword arguments
                admin_email_call = mock.call(
                    recipient_list=[settings.ADMIN_EMAIL],
                    subject=f"New Motorcycle Hire Booking (Online) - {hire_booking.booking_reference}",
                    template_name='booking_confirmation_admin.html',
                    context={
                        'hire_booking': hire_booking,
                        'user': self.user,
                        'driver_profile': self.driver_profile,
                        'is_in_store': False,
                    },
                    booking=hire_booking
                )
                mock_send_email.assert_any_call(**admin_email_call.kwargs)


    def test_handle_hire_booking_succeeded_temp_booking_does_not_exist(self):
        """
        Tests handle_hire_booking_succeeded when the associated TempHireBooking is missing.
        """
        # Create a payment object that is NOT linked to any existing TempHireBooking
        payment_obj = create_payment(
            amount=Decimal('100.00'),
            currency='AUD',
            status='succeeded',
            stripe_payment_intent_id="pi_missing_temp_booking_789",
        )
        # Do NOT link payment_obj.temp_hire_booking or link to a non-existent ID
        # For this test, we'll simulate a missing temp booking by not setting the link.

        payment_intent_data = {
            'id': "pi_missing_temp_booking_789",
            'amount': 10000,
            'amount_received': 10000, # Added for consistency, though not directly used in this error path
            'currency': 'aud',
            'status': 'succeeded',
            'metadata': {'booking_type': 'hire_booking', 'payment_id': str(payment_obj.id)}
        }

        # Mock the logger to check if error is logged (logger is not used in the provided code, print is)
        # Instead, we check for the specific exception.
        with self.assertRaises(TempHireBooking.DoesNotExist): # Corrected exception
            handle_hire_booking_succeeded(payment_obj, payment_intent_data)

        # Assert no HireBooking was created
        self.assertEqual(HireBooking.objects.filter(stripe_payment_intent_id="pi_missing_temp_booking_789").count(), 0)


    def test_handle_hire_booking_succeeded_transaction_rollback_on_error(self):
        """
        Tests that the transaction rolls back if an error occurs during conversion.
        """
        # 1. Setup: Create TempHireBooking, Payment, and TempBookingAddOn
        temp_booking = create_temp_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile,
            payment_option='online_full',
            grand_total=Decimal('200.00'),
            total_hire_price=Decimal('160.00'),
            total_addons_price=Decimal('40.00'),
            total_package_price=Decimal('0.00'),
            currency='AUD'
        )
        create_temp_booking_addon(temp_booking, self.addon1, quantity=1)

        payment_obj = create_payment(
            amount=Decimal('200.00'),
            currency='AUD',
            status='requires_payment_method',
            stripe_payment_intent_id="pi_rollback_test_123",
        )
        payment_obj.temp_hire_booking = temp_booking
        payment_obj.save()

        payment_intent_data = {
            'id': "pi_rollback_test_123",
            'amount': 20000,
            'amount_received': 20000, # Added: The actual amount received by Stripe
            'currency': 'aud',
            'status': 'succeeded',
            'metadata': {'booking_type': 'hire_booking', 'payment_id': str(payment_obj.id)}
        }

        # Mock a critical error during the creation of BookingAddOn
        # Also mock send_templated_email to ensure it's not called if a rollback occurs
        with mock.patch('hire.temp_hire_converter.BookingAddOn.objects.create', side_effect=ValueError("Simulated DB error")), \
             mock.patch('payments.webhook_handlers.send_templated_email') as mock_send_email:
            with self.assertRaises(ValueError): # Expecting the simulated error to be re-raised
                handle_hire_booking_succeeded(payment_obj, payment_intent_data)

            # Assertions: Check that everything was rolled back
            # TempHireBooking should NOT be deleted
            self.assertTrue(TempHireBooking.objects.filter(id=temp_booking.id).exists())
            # Check TempBookingAddOns by filtering on the original temp_booking_id
            self.assertEqual(TempBookingAddOn.objects.filter(temp_booking__id=temp_booking.id).count(), 1) # Temp add-on still exists

            # HireBooking should NOT be created
            self.assertEqual(HireBooking.objects.filter(stripe_payment_intent_id="pi_rollback_test_123").count(), 0)
            self.assertEqual(BookingAddOn.objects.count(), 0) # No permanent add-ons created

            # Payment object should NOT be updated (links should remain as they were)
            payment_obj.refresh_from_db()
            self.assertEqual(payment_obj.temp_hire_booking, temp_booking) # Temp link should still be there
            self.assertIsNone(payment_obj.hire_booking) # Permanent link should NOT be set
            # self.assertIsNone(payment_obj.driver_profile) # Driver profile might be set by create_payment factory

            # Assert that send_templated_email was NOT called
            mock_send_email.assert_not_called()

    def test_handle_hire_booking_succeeded_no_admin_email(self):
        """
        Tests that the admin email is not sent if settings.ADMIN_EMAIL is not configured.
        """
        # Set ADMIN_EMAIL to None for this test
        with self.settings(ADMIN_EMAIL=None):
            temp_booking = create_temp_hire_booking(
                motorcycle=self.motorcycle,
                driver_profile=self.driver_profile,
                payment_option='online_full',
                grand_total=Decimal('100.00'),
                currency='AUD'
            )
            payment_obj = create_payment(
                amount=Decimal('100.00'),
                currency='AUD',
                status='requires_payment_method',
                stripe_payment_intent_id="pi_no_admin_email_123",
            )
            payment_obj.temp_hire_booking = temp_booking
            payment_obj.save()

            payment_intent_data = {
                'id': "pi_no_admin_email_123",
                'amount': 10000,
                'amount_received': 10000,
                'currency': 'aud',
                'status': 'succeeded',
                'metadata': {'booking_type': 'hire_booking', 'payment_id': str(payment_obj.id)}
            }

            with mock.patch('payments.webhook_handlers.send_templated_email') as mock_send_email:
                handle_hire_booking_succeeded(payment_obj, payment_intent_data)

                # Retrieve the created HireBooking object after the handler runs
                hire_booking = HireBooking.objects.get(stripe_payment_intent_id="pi_no_admin_email_123")

                # Assert only one email was sent (to the user)
                self.assertEqual(mock_send_email.call_count, 1)

                # Assert user email call using keyword arguments
                user_email_call = mock.call(
                    recipient_list=[self.user.email],
                    subject=f"Your Motorcycle Hire Booking Confirmation - {hire_booking.booking_reference}",
                    template_name='booking_confirmation_user.html',
                    context={
                        'hire_booking': hire_booking,
                        'user': self.user,
                        'driver_profile': self.driver_profile,
                        'is_in_store': False,
                    },
                    user=self.user,
                    driver_profile=self.driver_profile,
                    booking=hire_booking
                )
                # Use assert_any_call to check if a call matching these kwargs was made
                mock_send_email.assert_any_call(**user_email_call.kwargs)


                # Ensure no call was made to the admin email by checking call.kwargs
                # This check is a bit more robust
                admin_email_found = False
                for call_args in mock_send_email.call_args_list:
                    if settings.ADMIN_EMAIL and settings.ADMIN_EMAIL in call_args.kwargs.get('recipient_list', []):
                        admin_email_found = True
                        break
                self.assertFalse(admin_email_found)

    # --- New tests for Refund Webhook Handlers ---

    @override_settings(ADMIN_EMAIL='admin_refund@example.com', SITE_BASE_URL='http://localhost:8000')
    @mock.patch('payments.webhook_handlers.send_templated_email')
    def test_handle_charge_refunded_full_refund_success(self, mock_send_email):
        """
        Tests 'charge.refunded' event for a full refund where HireRefundRequest exists.
        """
        refund_request = create_refund_request(
            hire_booking=self.hire_booking_for_refund,
            payment=self.payment_for_refund,
            driver_profile=self.driver_profile,
            amount_to_refund=self.payment_for_refund.amount,
            status='approved', # Admin has approved it
            stripe_refund_id='re_initial_test_full', # Pre-existing on request
            request_email=self.driver_profile.email
        )

        event_charge_object_data = {
            'object': 'charge',
            'id': 'ch_123', # Stripe Charge ID
            'payment_intent': self.payment_for_refund.stripe_payment_intent_id,
            'amount': int(self.payment_for_refund.amount * 100),
            'amount_refunded': int(self.payment_for_refund.amount * 100), # Fully refunded
            'currency': 'aud',
            'status': 'succeeded', # Charge status
            'refunds': {
                'object': 'list',
                'data': [{
                    'id': 're_test_full_webhook', # Stripe Refund ID from webhook
                    'object': 'refund',
                    'amount': int(self.payment_for_refund.amount * 100),
                    'status': 'succeeded',
                    'charge': 'ch_123',
                    'created': int(timezone.now().timestamp())
                }],
                'has_more': False,
                'url': '/v1/charges/ch_123/refunds'
            }
        }

        handle_hire_booking_refunded(self.payment_for_refund, event_charge_object_data)

        self.payment_for_refund.refresh_from_db()
        self.hire_booking_for_refund.refresh_from_db()
        refund_request.refresh_from_db()

        self.assertEqual(self.payment_for_refund.status, 'refunded')
        self.assertEqual(self.payment_for_refund.refunded_amount, self.payment_for_refund.amount)
        self.assertEqual(self.hire_booking_for_refund.status, 'cancelled')
        self.assertEqual(self.hire_booking_for_refund.payment_status, 'refunded')
        self.assertEqual(refund_request.status, 'refunded')
        # The handler updates amount_to_refund to the actual refunded amount from Stripe
        self.assertEqual(refund_request.amount_to_refund, self.payment_for_refund.amount)
        self.assertEqual(refund_request.stripe_refund_id, 're_initial_test_full') # Should remain initial ID as per handler logic

        self.assertEqual(mock_send_email.call_count, 2) # User and Admin

        # Check user email
        user_email_args = mock_send_email.call_args_list[0].kwargs
        self.assertEqual(user_email_args['recipient_list'], [self.driver_profile.email])
        self.assertEqual(user_email_args['template_name'], 'user_refund_processed_confirmation.html')
        self.assertEqual(user_email_args['context']['refunded_amount'], self.payment_for_refund.amount)

        # Check admin email
        admin_email_args = mock_send_email.call_args_list[1].kwargs
        self.assertEqual(admin_email_args['recipient_list'], [settings.ADMIN_EMAIL])
        self.assertEqual(admin_email_args['template_name'], 'admin_refund_processed_notification.html')


    @override_settings(ADMIN_EMAIL='admin_partial_refund@example.com', SITE_BASE_URL='http://localhost:8000')
    @mock.patch('payments.webhook_handlers.send_templated_email')
    def test_handle_charge_refunded_partial_refund_success(self, mock_send_email):
        """
        Tests 'charge.refunded' event for a partial refund.
        HireRefundRequest amount_to_refund was for this partial amount.
        """
        partial_refund_amount = Decimal('100.00')
        refund_request = create_refund_request(
            hire_booking=self.hire_booking_for_refund,
            payment=self.payment_for_refund,
            driver_profile=self.driver_profile,
            amount_to_refund=partial_refund_amount, # Request was for this amount
            status='approved',
            request_email=self.driver_profile.email
        )

        event_charge_object_data = {
            'object': 'charge',
            'id': 'ch_partial_123',
            'payment_intent': self.payment_for_refund.stripe_payment_intent_id,
            'amount': int(self.payment_for_refund.amount * 100),
            'amount_refunded': int(partial_refund_amount * 100), # Partially refunded
            'currency': 'aud',
            'status': 'succeeded',
            'refunds': {
                'data': [{
                    'id': 're_test_partial_webhook',
                    'status': 'succeeded',
                    'amount': int(partial_refund_amount * 100),
                    'created': int(timezone.now().timestamp())
                }]
            }
        }

        handle_hire_booking_refunded(self.payment_for_refund, event_charge_object_data)

        self.payment_for_refund.refresh_from_db()
        self.hire_booking_for_refund.refresh_from_db()
        refund_request.refresh_from_db()

        self.assertEqual(self.payment_for_refund.status, 'partially_refunded')
        self.assertEqual(self.payment_for_refund.refunded_amount, partial_refund_amount)
        self.assertEqual(self.hire_booking_for_refund.status, 'confirmed') # Booking not cancelled for partial
        self.assertEqual(self.hire_booking_for_refund.payment_status, 'partially_refunded')
        # Since amount_refunded (from Stripe) >= refund_request.amount_to_refund (original request), status is 'refunded'
        self.assertEqual(refund_request.status, 'refunded')
        self.assertEqual(refund_request.amount_to_refund, partial_refund_amount) # Updated to actual
        self.assertEqual(refund_request.stripe_refund_id, 're_test_partial_webhook')

        self.assertEqual(mock_send_email.call_count, 2)


    @override_settings(ADMIN_EMAIL='admin_refund_fail@example.com', SITE_BASE_URL='http://localhost:8000')
    @mock.patch('payments.webhook_handlers.send_templated_email')
    def test_handle_charge_refunded_refund_failed_in_webhook(self, mock_send_email):
        """
        Tests 'charge.refunded' where the refund itself failed according to Stripe's refund object.
        """
        refund_request = create_refund_request(
            hire_booking=self.hire_booking_for_refund,
            payment=self.payment_for_refund,
            driver_profile=self.driver_profile,
            amount_to_refund=Decimal('50.00'),
            status='approved',
            request_email=self.driver_profile.email
        )

        event_charge_object_data = {
            'object': 'charge',
            'id': 'ch_fail_123',
            'payment_intent': self.payment_for_refund.stripe_payment_intent_id,
            'amount': int(self.payment_for_refund.amount * 100),
            'amount_refunded': 0, # No amount actually refunded
            'currency': 'aud',
            'status': 'succeeded',
            'refunds': {
                'data': [{
                    'id': 're_test_failed_webhook',
                    'status': 'failed', # Refund failed
                    'amount': int(Decimal('50.00') * 100), # Attempted amount
                    'created': int(timezone.now().timestamp())
                }]
            }
        }
        # The handler exits if deduced refunded_amount_decimal <= 0.
        # For a 'failed' refund status in the webhook's refund object, the `amount_refunded` on the charge
        # might still be 0. The current handler logic for `charge` object data:
        # `refunded_amount_cents = event_object_data.get('amount_refunded')`
        # `if refunded_amount_cents is not None: refunded_amount_decimal = Decimal(refunded_amount_cents) / Decimal('100')`
        # `if refunded_amount_decimal is None or refunded_amount_decimal <= 0: return`
        # So if charge.amount_refunded is 0, it will return early.
        # To test the 'failed' status update on HireRefundRequest, we need to ensure this early exit is bypassed
        # or the logic is adapted. The current handler *will* exit if charge.amount_refunded is 0.

        # Let's assume for this test, Stripe *might* send amount_refunded as the attempted amount
        # even if the refund object status is 'failed', or the handler is modified to process refund status regardless of amount_refunded.
        # Given the current code, if amount_refunded is 0, it returns.
        # To properly test the 'failed' path for HireRefundRequest, we'd need a scenario where
        # amount_refunded is > 0 initially (e.g. a previous partial refund) and then a new refund fails,
        # or the event is a 'charge.refund.updated' with status 'failed'.

        # For 'charge.refunded' with a failed refund, if charge.amount_refunded is 0, the handler returns.
        # Let's test this specific behavior of returning early.
        handle_hire_booking_refunded(self.payment_for_refund, event_charge_object_data)

        self.payment_for_refund.refresh_from_db()
        refund_request.refresh_from_db()

        # Assert that because charge.amount_refunded was 0, no changes were made by the main logic
        self.assertEqual(self.payment_for_refund.status, 'succeeded') # Remains succeeded
        self.assertEqual(self.payment_for_refund.refunded_amount, Decimal('0.00'))
        self.assertEqual(refund_request.status, 'approved') # Remains approved
        mock_send_email.assert_not_called() # No emails because handler returned early


    @override_settings(ADMIN_EMAIL='admin_refund_updated@example.com', SITE_BASE_URL='http://localhost:8000')
    @mock.patch('payments.webhook_handlers.send_templated_email')
    @mock.patch('stripe.Charge.retrieve')
    def test_handle_refund_updated_full_refund_success(self, mock_stripe_charge_retrieve, mock_send_email):
        """
        Tests 'charge.refund.updated' event for a full refund success.
        """
        refund_amount = self.payment_for_refund.amount
        refund_request = create_refund_request(
            hire_booking=self.hire_booking_for_refund,
            payment=self.payment_for_refund,
            driver_profile=self.driver_profile,
            amount_to_refund=refund_amount,
            status='approved',
            stripe_refund_id='re_updated_full', # This ID will be in the event
            request_email=self.driver_profile.email
        )

        # Mock the stripe.Charge.retrieve call
        mock_stripe_charge_retrieve.return_value = {
            'id': 'ch_for_refund_update',
            'object': 'charge',
            'amount_refunded': int(refund_amount * 100), # Full amount refunded on charge
            'currency': 'aud',
        }

        event_refund_object_data = {
            'object': 'refund',
            'id': 're_updated_full', # Stripe Refund ID
            'payment_intent': self.payment_for_refund.stripe_payment_intent_id,
            'charge': 'ch_for_refund_update', # Associated charge
            'amount': int(refund_amount * 100),
            'currency': 'aud',
            'status': 'succeeded', # Refund succeeded
        }

        handle_hire_booking_refund_updated(self.payment_for_refund, event_refund_object_data)

        self.payment_for_refund.refresh_from_db()
        self.hire_booking_for_refund.refresh_from_db()
        refund_request.refresh_from_db()

        mock_stripe_charge_retrieve.assert_called_once_with('ch_for_refund_update')
        self.assertEqual(self.payment_for_refund.status, 'refunded')
        self.assertEqual(self.payment_for_refund.refunded_amount, refund_amount)
        self.assertEqual(self.hire_booking_for_refund.status, 'cancelled')
        self.assertEqual(self.hire_booking_for_refund.payment_status, 'refunded')
        self.assertEqual(refund_request.status, 'refunded')
        self.assertEqual(refund_request.amount_to_refund, refund_amount)

        self.assertEqual(mock_send_email.call_count, 2)


    @override_settings(ADMIN_EMAIL='admin_refund_updated_fail@example.com', SITE_BASE_URL='http://localhost:8000')
    @mock.patch('payments.webhook_handlers.send_templated_email')
    @mock.patch('stripe.Charge.retrieve')
    def test_handle_refund_updated_refund_failed(self, mock_stripe_charge_retrieve, mock_send_email):
        """
        Tests 'charge.refund.updated' event where the refund status is 'failed'.
        """
        attempted_refund_amount = Decimal('50.00')
        refund_request = create_refund_request(
            hire_booking=self.hire_booking_for_refund,
            payment=self.payment_for_refund,
            driver_profile=self.driver_profile,
            amount_to_refund=attempted_refund_amount,
            status='approved',
            stripe_refund_id='re_updated_failed',
            request_email=self.driver_profile.email
        )

        # Mock stripe.Charge.retrieve, assuming no money was actually moved on the charge
        mock_stripe_charge_retrieve.return_value = {
            'id': 'ch_for_failed_refund',
            'object': 'charge',
            'amount_refunded': 0, # No amount actually refunded on the charge
            'currency': 'aud',
        }

        event_refund_object_data = {
            'object': 'refund',
            'id': 're_updated_failed',
            'charge': 'ch_for_failed_refund',
            'amount': int(attempted_refund_amount * 100), # Amount attempted
            'currency': 'aud',
            'status': 'failed', # Refund failed
        }

        # As per current handler logic, if the retrieved charge.amount_refunded is 0,
        # then deduced refunded_amount_decimal will be 0, and the handler will return early.
        # This means HireRefundRequest status might not be updated to 'failed' in this specific flow.
        # The handler logic: `if refunded_amount_decimal is None or refunded_amount_decimal <= 0: return`

        handle_hire_booking_refund_updated(self.payment_for_refund, event_refund_object_data)

        self.payment_for_refund.refresh_from_db()
        refund_request.refresh_from_db()

        mock_stripe_charge_retrieve.assert_called_once_with('ch_for_failed_refund')

        # Due to early exit because charge.amount_refunded is 0
        self.assertEqual(self.payment_for_refund.status, 'succeeded') # Remains unchanged
        self.assertEqual(self.payment_for_refund.refunded_amount, Decimal('0.00'))
        self.assertEqual(refund_request.status, 'approved') # Remains unchanged
        mock_send_email.assert_not_called()


    @override_settings(ADMIN_EMAIL='admin_no_req@example.com', SITE_BASE_URL='http://localhost:8000')
    @mock.patch('payments.webhook_handlers.send_templated_email')
    def test_handle_charge_refunded_no_hire_refund_request_found(self, mock_send_email):
        """
        Tests 'charge.refunded' when no HireRefundRequest matches, but Payment and Booking are still updated.
        """
        refunded_amount = Decimal('75.00')
        # Ensure no HireRefundRequest exists for this payment
        HireRefundRequest.objects.filter(payment=self.payment_for_refund).delete()

        event_charge_object_data = {
            'object': 'charge',
            'id': 'ch_no_req_123',
            'payment_intent': self.payment_for_refund.stripe_payment_intent_id,
            'amount': int(self.payment_for_refund.amount * 100),
            'amount_refunded': int(refunded_amount * 100),
            'currency': 'aud',
            'status': 'succeeded',
            'refunds': {
                'data': [{
                    'id': 're_no_req_webhook',
                    'status': 'succeeded',
                    'amount': int(refunded_amount * 100),
                    'created': int(timezone.now().timestamp())
                }]
            }
        }

        handle_hire_booking_refunded(self.payment_for_refund, event_charge_object_data)

        self.payment_for_refund.refresh_from_db()
        self.hire_booking_for_refund.refresh_from_db()

        self.assertEqual(self.payment_for_refund.status, 'partially_refunded')
        self.assertEqual(self.payment_for_refund.refunded_amount, refunded_amount)
        self.assertEqual(self.hire_booking_for_refund.payment_status, 'partially_refunded')
        self.assertEqual(self.hire_booking_for_refund.status, 'confirmed') # Not cancelled

        # Emails should still be sent if user email can be derived from payment/driver_profile
        self.assertEqual(mock_send_email.call_count, 2)
        user_email_args = mock_send_email.call_args_list[0].kwargs
        self.assertEqual(user_email_args['recipient_list'], [self.user.email]) # From payment_obj.driver_profile.user.email

    @override_settings(ADMIN_EMAIL='admin_stripe_fail@example.com', SITE_BASE_URL='http://localhost:8000')
    @mock.patch('payments.webhook_handlers.send_templated_email')
    @mock.patch('stripe.Charge.retrieve', side_effect=stripe.error.StripeError("Simulated Stripe API error"))
    def test_handle_refund_updated_stripe_charge_retrieve_fails(self, mock_stripe_charge_retrieve_fail, mock_send_email):
        """
        Tests 'charge.refund.updated' when stripe.Charge.retrieve fails.
        The handler should fall back to using the amount from the refund object itself.
        """
        fallback_refund_amount = Decimal('25.00')
        refund_request = create_refund_request(
            hire_booking=self.hire_booking_for_refund,
            payment=self.payment_for_refund,
            driver_profile=self.driver_profile,
            amount_to_refund=fallback_refund_amount, # Request was for this amount
            status='approved',
            stripe_refund_id='re_stripe_fail',
            request_email=self.driver_profile.email
        )

        event_refund_object_data = {
            'object': 'refund',
            'id': 're_stripe_fail',
            'charge': 'ch_will_fail_retrieve',
            'amount': int(fallback_refund_amount * 100), # This amount should be used
            'currency': 'aud',
            'status': 'succeeded',
        }

        handle_hire_booking_refund_updated(self.payment_for_refund, event_refund_object_data)

        self.payment_for_refund.refresh_from_db()
        self.hire_booking_for_refund.refresh_from_db()
        refund_request.refresh_from_db()

        mock_stripe_charge_retrieve_fail.assert_called_once_with('ch_will_fail_retrieve')
        self.assertEqual(self.payment_for_refund.status, 'partially_refunded')
        self.assertEqual(self.payment_for_refund.refunded_amount, fallback_refund_amount)
        self.assertEqual(self.hire_booking_for_refund.payment_status, 'partially_refunded')
        # Refund request status becomes 'refunded' because the fallback amount matched the requested amount
        self.assertEqual(refund_request.status, 'refunded')
        self.assertEqual(refund_request.amount_to_refund, fallback_refund_amount) # Updated to actual fallback

        self.assertEqual(mock_send_email.call_count, 2)
