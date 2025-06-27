import datetime
from decimal import Decimal
import stripe
from unittest import skipIf, mock

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.conf import settings
from django.core import mail
from django.utils import timezone

from inventory.models import TempSalesBooking, SalesBooking, SalesProfile, Motorcycle
from payments.models import Payment
from ..test_helpers.model_factories import (
    InventorySettingsFactory,
    MotorcycleFactory,
    UserFactory,
)
from payments.webhook_handlers.sales_handlers import handle_sales_booking_succeeded

@override_settings(ADMIN_EMAIL='ethan.betts.dev@gmail.com')
class TestEnquiryFlows(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = UserFactory()
        self.client.force_login(self.user)
        self.settings = InventorySettingsFactory(currency_code='AUD')
        self.motorcycle = MotorcycleFactory(
            is_available=True,
            status='available',
            price=Decimal('5000.00'),
            year=1993,
            brand='Kawasaki',
            model='Enough'
        )
        self.another_motorcycle = MotorcycleFactory(
            is_available=True, status='available', price=Decimal('8000.00')
        )

    def test_enquiry_with_appointment_flow(self):
        initiate_url = reverse('inventory:initiate_booking', kwargs={'pk': self.motorcycle.pk})
        response = self.client.post(initiate_url, {'deposit_required_for_flow': 'false'})
        self.assertEqual(response.status_code, 302)
        self.assertIn('temp_sales_booking_uuid', self.client.session)

        step1_url = reverse('inventory:step1_sales_profile')
        profile_data = {'name': 'Enquiry User', 'email': 'enquiry@example.com', 'phone_number': '555-0000'}
        response = self.client.post(step1_url, profile_data)
        self.assertRedirects(response, reverse('inventory:step2_booking_details_and_appointment'))

        step2_url = reverse('inventory:step2_booking_details_and_appointment')
        appointment_data = {
            'request_viewing': 'yes',
            'appointment_date': '2025-10-20',
            'appointment_time': '10:00',
            'terms_accepted': 'on',
            'customer_notes': 'I would like to come see this bike.'
        }
        response = self.client.post(step2_url, appointment_data)

        self.assertRedirects(response, reverse('inventory:step4_confirmation'))
        self.assertEqual(TempSalesBooking.objects.count(), 0)
        self.assertEqual(SalesBooking.objects.count(), 1)
        
        final_booking = SalesBooking.objects.first()
        self.assertEqual(final_booking.payment_status, 'unpaid')
        self.assertIsNotNone(final_booking.appointment_date)

        self.motorcycle.refresh_from_db()
        self.assertEqual(self.motorcycle.status, 'available')
        
        confirmation_response = self.client.get(response.url)
        self.assertEqual(confirmation_response.status_code, 200)
        self.assertContains(confirmation_response, "Thank you for your enquiry!")
        self.assertContains(confirmation_response, final_booking.sales_booking_reference)

        self.assertEqual(len(mail.outbox), 2)
        self.assertIn('Your Motorcycle Appointment Request', mail.outbox[0].subject)
        
        self.assertIn('recent_booking_flag', self.client.session)
        initiate_blocked_url = reverse('inventory:initiate_booking', kwargs={'pk': self.another_motorcycle.pk})
        response_blocked = self.client.post(initiate_blocked_url, {'deposit_required_for_flow': 'false'})
        self.assertRedirects(response_blocked, reverse('inventory:step1_sales_profile'))
        
        final_response_blocked = self.client.get(response_blocked.url, follow=True)
        self.assertRedirects(final_response_blocked, reverse('inventory:all'), target_status_code=200)
        messages = list(final_response_blocked.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertIn("You have recently made a booking", str(messages[0]))


    def test_enquiry_without_appointment_flow(self):
        initiate_url = reverse('inventory:initiate_booking', kwargs={'pk': self.motorcycle.pk})
        self.client.post(initiate_url, {'deposit_required_for_flow': 'false'})

        step1_url = reverse('inventory:step1_sales_profile')
        profile_data = {'name': 'Message User', 'email': 'message@example.com', 'phone_number': '555-1111'}
        self.client.post(step1_url, profile_data)

        step2_url = reverse('inventory:step2_booking_details_and_appointment')
        enquiry_data = {
            'request_viewing': 'no',
            'terms_accepted': 'on',
            'customer_notes': 'Just wondering about the service history.'
        }
        response = self.client.post(step2_url, enquiry_data)

        self.assertRedirects(response, reverse('inventory:step4_confirmation'))
        self.assertEqual(SalesBooking.objects.count(), 1)
        
        final_booking = SalesBooking.objects.first()
        self.assertEqual(final_booking.payment_status, 'unpaid')
        self.assertIsNone(final_booking.appointment_date)

        self.motorcycle.refresh_from_db()
        self.assertEqual(self.motorcycle.status, 'available')
        self.assertTrue(self.motorcycle.is_available)

        confirmation_response = self.client.get(response.url)
        self.assertEqual(confirmation_response.status_code, 200)
        self.assertContains(confirmation_response, "Your enquiry has been submitted. We will get back to you shortly!")

        self.assertEqual(len(mail.outbox), 2)
        self.assertIn('Your Motorcycle Enquiry Received', mail.outbox[0].subject)

        self.assertIn('recent_booking_flag', self.client.session)
        with mock.patch('django.utils.timezone.now') as mock_now:
            current_time = self.client.session.get('recent_booking_flag')
            mock_now.return_value = timezone.make_aware(datetime.datetime.fromisoformat(current_time)) + datetime.timedelta(minutes=6)

            initiate_allowed_url = reverse('inventory:initiate_booking', kwargs={'pk': self.another_motorcycle.pk})
            response_allowed = self.client.post(initiate_allowed_url, {'deposit_required_for_flow': 'false'})
            self.assertRedirects(response_allowed, reverse('inventory:step1_sales_profile'))
            
            final_response_allowed = self.client.get(response_allowed.url)
            self.assertEqual(final_response_allowed.status_code, 200)
            self.assertNotContains(final_response_allowed, "You have recently made a booking")



@skipIf(not settings.STRIPE_SECRET_KEY, "Stripe API key not configured in settings")
class TestDepositFlows(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = UserFactory()
        self.client.force_login(self.user)
        self.settings = InventorySettingsFactory(
            enable_reservation_by_deposit=True,
            deposit_amount=Decimal('150.00'),
            currency_code='AUD'
        )
        self.motorcycle = MotorcycleFactory(
            is_available=True,
            price=Decimal('12000.00'),
            status='available',
            year=1999,
            brand='Kawasaki',
            model='Star'
        )
        stripe.api_key = settings.STRIPE_SECRET_KEY

    def test_deposit_with_appointment_flow(self):
        initiate_url = reverse('inventory:initiate_booking', kwargs={'pk': self.motorcycle.pk})
        response = self.client.post(initiate_url, {'deposit_required_for_flow': 'true'})
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('temp_sales_booking_uuid', self.client.session)
        self.assertEqual(TempSalesBooking.objects.count(), 1)
        temp_booking = TempSalesBooking.objects.first()
        self.assertEqual(temp_booking.motorcycle, self.motorcycle)
        self.assertTrue(temp_booking.deposit_required_for_flow)

        step1_url = reverse('inventory:step1_sales_profile')
        profile_data = {
            'name': 'Thorough Tester',
            'email': 'thorough.tester@example.com',
            'phone_number': '555-1234'
        }
        response = self.client.post(step1_url, profile_data)

        self.assertRedirects(response, reverse('inventory:step2_booking_details_and_appointment'))
        temp_booking.refresh_from_db()
        self.assertIsNotNone(temp_booking.sales_profile)
        self.assertEqual(temp_booking.sales_profile.name, 'Thorough Tester')
        self.assertEqual(SalesProfile.objects.count(), 1)
        
        step2_url = reverse('inventory:step2_booking_details_and_appointment')
        appointment_data = {
            'request_viewing': 'yes',
            'appointment_date': '2025-09-15',
            'appointment_time': '14:00',
            'terms_accepted': 'on'
        }
        response = self.client.post(step2_url, appointment_data)

        self.assertRedirects(response, reverse('inventory:step3_payment'))
        temp_booking.refresh_from_db()
        self.assertEqual(temp_booking.appointment_date, datetime.date(2025, 9, 15))
        self.assertEqual(temp_booking.appointment_time, datetime.time(14, 0))
        self.assertTrue(temp_booking.terms_accepted)

        step3_url = reverse('inventory:step3_payment')
        response = self.client.get(step3_url)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(Payment.objects.count(), 1)
        payment_obj = Payment.objects.first()
        self.assertEqual(payment_obj.amount, self.settings.deposit_amount)
        self.assertEqual(payment_obj.temp_sales_booking, temp_booking)
        payment_intent_id = payment_obj.stripe_payment_intent_id
        self.assertIsNotNone(payment_intent_id)

        try:
            confirmation_url_path = reverse('inventory:step4_confirmation')
            full_return_url = f"http://testserver{confirmation_url_path}"
            stripe.PaymentIntent.confirm(
                payment_intent_id,
                payment_method="pm_card_visa",
                return_url=full_return_url,
            )
        except stripe.error.StripeError as e:
            self.fail(f"Stripe API call failed during test: {e}")

        updated_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        handle_sales_booking_succeeded(payment_obj, updated_intent)

        self.assertEqual(TempSalesBooking.objects.count(), 0)
        self.assertEqual(SalesBooking.objects.count(), 1)
        
        final_booking = SalesBooking.objects.first()
        self.assertEqual(final_booking.payment_status, 'deposit_paid')
        self.assertEqual(final_booking.amount_paid, self.settings.deposit_amount)
        self.assertEqual(final_booking.sales_profile.name, 'Thorough Tester')
        self.assertEqual(final_booking.appointment_date, datetime.date(2025, 9, 15))

        self.motorcycle.refresh_from_db()
        self.assertEqual(self.motorcycle.status, 'reserved')
        self.assertFalse(self.motorcycle.is_available)
        
        payment_obj.refresh_from_db()
        self.assertEqual(payment_obj.status, 'succeeded')
        self.assertEqual(payment_obj.sales_booking, final_booking)

        confirmation_url = reverse('inventory:step4_confirmation') + f'?payment_intent_id={payment_intent_id}'
        response = self.client.get(confirmation_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, final_booking.sales_booking_reference)
        
        another_user_client = Client()
        another_user = UserFactory(username="another_user")
        another_user_client.force_login(another_user)
        
        initiate_url_blocked = reverse('inventory:initiate_booking', kwargs={'pk': self.motorcycle.pk})
        response_blocked = another_user_client.post(initiate_url_blocked, {'deposit_required_for_flow': 'true'}, follow=True)
        self.assertRedirects(response_blocked, reverse('inventory:all'), target_status_code=200)
        messages = list(response_blocked.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertIn("Sorry, this motorcycle has just been reserved or sold", str(messages[0]))
