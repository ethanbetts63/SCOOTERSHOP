from decimal import Decimal
from django.test import TestCase, override_settings
from django.core.exceptions import ObjectDoesNotExist
from unittest import mock
from django.conf import settings

# Import models
from hire.models import HireBooking, TempHireBooking, BookingAddOn, TempBookingAddOn
from payments.models import Payment

# Import the handler
from payments.webhook_handlers.hire_handlers import handle_hire_booking_succeeded

# Import factories
from ..test_helpers.model_factories import (
    UserFactory,
    DriverProfileFactory,
    MotorcycleFactory,
    AddOnFactory,
    TempHireBookingFactory,
    TempBookingAddOnFactory,
    PaymentFactory,
    HireBookingFactory,
)

@override_settings(ADMIN_EMAIL='admin@example.com')
class HireWebhookHandlerTest(TestCase):
    """
    Tests for the hire-related webhook handlers.
    """
    @classmethod
    def setUpTestData(cls):
        """Set up non-modified objects used by all test methods."""
        cls.user = UserFactory(email="testuser@example.com")
        cls.driver_profile = DriverProfileFactory(user=cls.user)
        cls.motorcycle = MotorcycleFactory()
        cls.addon1 = AddOnFactory(name="GPS", daily_cost=Decimal('15.00'))
        cls.addon2 = AddOnFactory(name="Jacket", daily_cost=Decimal('25.00'))

    def test_handle_hire_booking_succeeded_full_payment(self):
        """
        Tests successful conversion from TempHireBooking to HireBooking on a full payment.
        """
        # 1. Setup
        temp_booking = TempHireBookingFactory(
            driver_profile=self.driver_profile,
            motorcycle=self.motorcycle,
            payment_option='online_full',
            grand_total=Decimal('240.00')
        )
        TempBookingAddOnFactory(temp_booking=temp_booking, addon=self.addon1)
        TempBookingAddOnFactory(temp_booking=temp_booking, addon=self.addon2)

        payment_obj = PaymentFactory(
            temp_hire_booking=temp_booking,
            amount=temp_booking.grand_total,
            status='requires_payment_method'
        )

        payment_intent_data = {
            'id': payment_obj.stripe_payment_intent_id,
            'amount_received': int(temp_booking.grand_total * 100),
            'status': 'succeeded',
        }

        # 2. Action
        with mock.patch('payments.webhook_handlers.hire_handlers.send_templated_email') as mock_send_email:
            handle_hire_booking_succeeded(payment_obj, payment_intent_data)

            # 3. Assertions
            # Assert TempBooking is gone
            with self.assertRaises(TempHireBooking.DoesNotExist):
                TempHireBooking.objects.get(id=temp_booking.id)

            # Assert HireBooking is created correctly
            hire_booking = HireBooking.objects.get(stripe_payment_intent_id=payment_obj.stripe_payment_intent_id)
            self.assertIsNotNone(hire_booking)
            self.assertEqual(hire_booking.payment_status, 'paid')
            self.assertEqual(hire_booking.status, 'confirmed')
            self.assertEqual(hire_booking.amount_paid, temp_booking.grand_total)
            self.assertEqual(BookingAddOn.objects.filter(booking=hire_booking).count(), 2)

            # Assert Payment object is updated
            payment_obj.refresh_from_db()
            self.assertEqual(payment_obj.status, 'succeeded')
            self.assertEqual(payment_obj.hire_booking, hire_booking)

            # Assert emails were sent
            self.assertEqual(mock_send_email.call_count, 2)
            # Check user email call
            mock_send_email.assert_any_call(
                recipient_list=[self.user.email],
                subject=f"Your Motorcycle Hire Booking Confirmation - {hire_booking.booking_reference}",
                template_name='booking_confirmation_user.html',
                context=mock.ANY,
                user=self.user,
                driver_profile=self.driver_profile,
                booking=hire_booking
            )
            # Check admin email call
            mock_send_email.assert_any_call(
                recipient_list=[settings.ADMIN_EMAIL],
                subject=f"New Motorcycle Hire Booking (Online) - {hire_booking.booking_reference}",
                template_name='booking_confirmation_admin.html',
                context=mock.ANY,
                booking=hire_booking
            )

    def test_handle_hire_booking_succeeded_deposit_payment(self):
        """
        Tests successful conversion on a deposit payment.
        """
        # 1. Setup
        temp_booking = TempHireBookingFactory(
            driver_profile=self.driver_profile,
            motorcycle=self.motorcycle,
            payment_option='online_deposit',
            grand_total=Decimal('300.00'),
            deposit_amount=Decimal('150.00')
        )
        payment_obj = PaymentFactory(
            temp_hire_booking=temp_booking,
            amount=temp_booking.deposit_amount,
            status='requires_payment_method'
        )
        payment_intent_data = {
            'id': payment_obj.stripe_payment_intent_id,
            'amount_received': int(temp_booking.deposit_amount * 100),
            'status': 'succeeded',
        }

        # 2. Action
        with mock.patch('payments.webhook_handlers.hire_handlers.send_templated_email') as mock_send_email:
            handle_hire_booking_succeeded(payment_obj, payment_intent_data)

            # 3. Assertions
            hire_booking = HireBooking.objects.get(stripe_payment_intent_id=payment_obj.stripe_payment_intent_id)
            self.assertEqual(hire_booking.payment_status, 'deposit_paid')
            self.assertEqual(hire_booking.amount_paid, temp_booking.deposit_amount)
            self.assertEqual(mock_send_email.call_count, 2)

    def test_handle_hire_booking_succeeded_temp_booking_missing(self):
        """
        Tests that an exception is raised if the TempHireBooking does not exist.
        """
        payment_obj = PaymentFactory(temp_hire_booking=None) # No link
        payment_intent_data = {'status': 'succeeded', 'amount_received': 10000}

        with self.assertRaises(TempHireBooking.DoesNotExist):
            handle_hire_booking_succeeded(payment_obj, payment_intent_data)

    def test_handle_hire_booking_succeeded_rollback_on_error(self):
        """
        Tests that the transaction rolls back if an error occurs during conversion.
        """
        temp_booking = TempHireBookingFactory()
        payment_obj = PaymentFactory(temp_hire_booking=temp_booking)
        payment_intent_data = {'status': 'succeeded', 'amount_received': 10000}

        # Mock a critical error during the process
        with mock.patch('payments.webhook_handlers.hire_handlers.convert_temp_to_hire_booking', side_effect=ValueError("Simulated DB error")):
            with self.assertRaises(ValueError):
                handle_hire_booking_succeeded(payment_obj, payment_intent_data)

            # Assertions: Check that everything was rolled back
            self.assertTrue(TempHireBooking.objects.filter(id=temp_booking.id).exists())
            self.assertFalse(HireBooking.objects.exists())
            payment_obj.refresh_from_db()
            self.assertIsNone(payment_obj.hire_booking)

