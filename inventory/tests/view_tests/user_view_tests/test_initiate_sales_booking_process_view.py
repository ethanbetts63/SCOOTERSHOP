from django.test import TestCase
from django.urls import reverse
from inventory.models import TempSalesBooking, InventorySettings
from inventory.tests.test_helpers.model_factories import MotorcycleFactory, InventorySettingsFactory
from django.contrib.messages import get_messages
from decimal import Decimal

class InitiateBookingProcessViewTest(TestCase):

    def setUp(self):
        self.motorcycle = MotorcycleFactory(status="for_sale")
        self.inventory_settings = InventorySettingsFactory()

    def test_post_initiate_booking_process_success_with_deposit(self):
        response = self.client.post(reverse('inventory:initiate_booking', kwargs={'pk': self.motorcycle.pk}), data={'deposit_required_for_flow': 'true'})
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('inventory:step1_sales_profile'))
        self.assertIn('temp_sales_booking_uuid', self.client.session)
        temp_booking = TempSalesBooking.objects.get(session_uuid=self.client.session['temp_sales_booking_uuid'])
        self.assertEqual(temp_booking.motorcycle, self.motorcycle)
        self.assertTrue(temp_booking.deposit_required_for_flow)
        self.assertEqual(temp_booking.amount_paid, self.inventory_settings.deposit_amount)
        self.assertEqual(temp_booking.booking_status, 'pending_details')

    def test_post_initiate_booking_process_success_without_deposit(self):
        response = self.client.post(reverse('inventory:initiate_booking', kwargs={'pk': self.motorcycle.pk}), data={'deposit_required_for_flow': 'false'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('temp_sales_booking_uuid', self.client.session)
        temp_booking = TempSalesBooking.objects.get(session_uuid=self.client.session['temp_sales_booking_uuid'])
        self.assertEqual(temp_booking.motorcycle, self.motorcycle)
        self.assertFalse(temp_booking.deposit_required_for_flow)
        self.assertEqual(temp_booking.amount_paid, Decimal('0.00'))
        self.assertEqual(temp_booking.booking_status, 'pending_details')

    def test_post_initiate_booking_process_motorcycle_not_available(self):
        not_for_sale_motorcycle = MotorcycleFactory(status="sold")
        response = self.client.post(reverse('inventory:initiate_booking', kwargs={'pk': not_for_sale_motorcycle.pk}))
        self.assertRedirects(response, reverse('inventory:motorcycle-detail', kwargs={'pk': not_for_sale_motorcycle.pk}))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn('is currently reserved or sold and cannot be booked at this time.', str(messages[0]))
        self.assertNotIn('temp_sales_booking_uuid', self.client.session)

    def test_post_initiate_booking_process_motorcycle_not_found(self):
        response = self.client.post(reverse('inventory:initiate_booking', kwargs={'pk': 999}))
        self.assertEqual(response.status_code, 404)
        self.assertNotIn('temp_sales_booking_uuid', self.client.session)

    def test_post_initiate_booking_process_no_inventory_settings(self):
        InventorySettings.objects.all().delete()
        response = self.client.post(reverse('inventory:initiate_booking', kwargs={'pk': self.motorcycle.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('inventory:all'))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn('Inventory settings are not configured.', str(messages[0]))
        self.assertNotIn('temp_sales_booking_uuid', self.client.session)