from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ObjectDoesNotExist
from unittest import mock
from django.conf import settings # Import settings to mock ADMIN_EMAIL

# Import model factories for easy test data creation
from hire.tests.test_helpers.model_factories import (
    create_motorcycle,
    create_driver_profile,
    create_hire_settings,
    create_payment,
    create_temp_hire_booking, # Added for conversion tests
    create_temp_booking_addon, # Added for conversion tests
    create_addon, # Added for conversion tests
    create_user, # Import create_user for email tests
)
from hire.models.hire_booking import HireBooking, PAYMENT_STATUS_CHOICES
from hire.models import TempHireBooking, BookingAddOn, TempBookingAddOn # Import for conversion tests

# Import the webhook handler
from payments.webhook_handlers import handle_hire_booking_succeeded

class WebhookHandlerTest(TestCase):
    """
    Tests for the webhook handler functions, specifically focusing on booking conversion.
    """
    @classmethod
    def setUpTestData(cls):
        cls.hire_settings = create_hire_settings(booking_lead_time_hours=0) # Set to 0 for easier date handling
        cls.motorcycle = create_motorcycle()
        # Create a user and link it to the driver profile for email testing
        cls.user = create_user(username="testuser", email="user@example.com")
        cls.driver_profile = create_driver_profile(user=cls.user, is_australian_resident=True, email="driver@example.com")
        cls.addon1 = create_addon(name="GPS", hourly_cost=Decimal('2.00'), daily_cost=Decimal('15.00'))
        cls.addon2 = create_addon(name="Jacket", hourly_cost=Decimal('5.00'), daily_cost=Decimal('25.00'))

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

        # Mock the logger to check if error is logged
        with mock.patch('payments.webhook_handlers.logger.error') as mock_logger_error:
            # The handler should now explicitly raise TempHireBooking.DoesNotExist
            with self.assertRaises(ObjectDoesNotExist):
                handle_hire_booking_succeeded(payment_obj, payment_intent_data)

            # Assert that the error was logged
            mock_logger_error.assert_called_with(
                f"TempHireBooking not found for Payment ID {payment_obj.id}. Cannot finalize booking."
            )

        # Assert no HireBooking was created
        self.assertEqual(HireBooking.objects.count(), 0)

        # Assert Payment object is NOT updated with hire_booking or driver_profile links
        payment_obj.refresh_from_db()
        self.assertIsNone(payment_obj.hire_booking)
        self.assertIsNone(payment_obj.driver_profile)


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
        with mock.patch('hire.models.BookingAddOn.objects.create', side_effect=ValueError("Simulated DB error")), \
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
            self.assertIsNone(payment_obj.driver_profile) # Driver profile link should NOT be set

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
                self.assertFalse(
                    any(
                        settings.ADMIN_EMAIL in call.kwargs.get('recipient_list', [])
                        for call in mock_send_email.call_args_list
                    )
                )
