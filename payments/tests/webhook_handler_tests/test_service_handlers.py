from decimal import Decimal
from django.test import TestCase, override_settings
from django.core.exceptions import ObjectDoesNotExist
from unittest import mock
from django.conf import settings

# Import models
from service.models import ServiceBooking, TempServiceBooking
from payments.models import Payment

# Import the handler
from payments.webhook_handlers.service_handlers import handle_service_booking_succeeded

# Import factories
from ..test_helpers.model_factories import (
    UserFactory,
    ServiceProfileFactory,
    CustomerMotorcycleFactory,
    ServiceTypeFactory,
    TempServiceBookingFactory,
    PaymentFactory,
    ServiceBookingFactory,
)

@override_settings(ADMIN_EMAIL='admin-service@example.com')
class ServiceWebhookHandlerTest(TestCase):
    """
    Tests for the service-related webhook handlers.
    """
    @classmethod
    def setUpTestData(cls):
        """Set up non-modified objects used by all test methods."""
        cls.user = UserFactory(email="serviceuser@example.com")
        cls.service_profile = ServiceProfileFactory(user=cls.user)
        cls.service_type = ServiceTypeFactory(base_price=Decimal('150.00'))
        cls.customer_motorcycle = CustomerMotorcycleFactory(service_profile=cls.service_profile)

    def test_handle_service_booking_succeeded(self):
        """
        Tests successful conversion from TempServiceBooking to ServiceBooking.
        """
        # 1. Setup
        temp_booking = TempServiceBookingFactory(
            service_profile=self.service_profile,
            customer_motorcycle=self.customer_motorcycle,
            service_type=self.service_type,
            payment_option='online_full',
            calculated_total=self.service_type.base_price
        )
        payment_obj = PaymentFactory(
            temp_service_booking=temp_booking,
            amount=temp_booking.calculated_total,
            status='requires_payment_method'
        )
        payment_intent_data = {
            'id': payment_obj.stripe_payment_intent_id,
            'amount_received': int(temp_booking.calculated_total * 100),
            'status': 'succeeded',
        }

        # 2. Action
        with mock.patch('payments.webhook_handlers.service_handlers.send_templated_email') as mock_send_email:
            handle_service_booking_succeeded(payment_obj, payment_intent_data)

            # 3. Assertions
            # Assert TempBooking is gone
            with self.assertRaises(TempServiceBooking.DoesNotExist):
                TempServiceBooking.objects.get(id=temp_booking.id)

            # Assert ServiceBooking is created correctly
            service_booking = ServiceBooking.objects.get(stripe_payment_intent_id=payment_obj.stripe_payment_intent_id)
            self.assertIsNotNone(service_booking)
            self.assertEqual(service_booking.payment_status, 'paid')
            self.assertEqual(service_booking.booking_status, 'confirmed')
            self.assertEqual(service_booking.amount_paid, temp_booking.calculated_total)

            # Assert Payment object is updated
            payment_obj.refresh_from_db()
            self.assertEqual(payment_obj.status, 'succeeded')
            self.assertEqual(payment_obj.service_booking, service_booking)

            # Assert emails were sent
            self.assertEqual(mock_send_email.call_count, 2)
            mock_send_email.assert_any_call(
                recipient_list=[self.user.email],
                subject=f"Your Service Booking Confirmation - {service_booking.service_booking_reference}",
                template_name='service_booking_confirmation_user.html',
                context=mock.ANY,
                booking=service_booking
            )
            mock_send_email.assert_any_call(
                recipient_list=[settings.ADMIN_EMAIL],
                subject=f"New Service Booking (Online) - {service_booking.service_booking_reference}",
                template_name='service_booking_confirmation_admin.html',
                context=mock.ANY,
                booking=service_booking
            )

    def test_handle_service_booking_succeeded_temp_booking_missing(self):
        """
        Tests that an exception is raised if the TempServiceBooking does not exist.
        """
        payment_obj = PaymentFactory(temp_service_booking=None) # No link
        payment_intent_data = {'status': 'succeeded', 'amount_received': 15000}

        with self.assertRaises(TempServiceBooking.DoesNotExist):
            handle_service_booking_succeeded(payment_obj, payment_intent_data)

    def test_handle_service_booking_succeeded_rollback_on_error(self):
        """
        Tests that the transaction rolls back if an error occurs during conversion.
        """
        temp_booking = TempServiceBookingFactory()
        payment_obj = PaymentFactory(temp_service_booking=temp_booking)
        payment_intent_data = {'status': 'succeeded', 'amount_received': 15000}

        # Mock a critical error during the process
        with mock.patch('payments.webhook_handlers.service_handlers.convert_temp_service_booking', side_effect=ValueError("Simulated DB error")):
            with self.assertRaises(ValueError):
                handle_service_booking_succeeded(payment_obj, payment_intent_data)

            # Assertions: Check that everything was rolled back
            self.assertTrue(TempServiceBooking.objects.filter(id=temp_booking.id).exists())
            self.assertFalse(ServiceBooking.objects.exists())
            payment_obj.refresh_from_db()
            self.assertIsNone(payment_obj.service_booking)
