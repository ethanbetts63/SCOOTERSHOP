import datetime
import uuid
from decimal import Decimal
from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.messages import get_messages

from inventory.models import Motorcycle
from hire.models import TempHireBooking
from dashboard.models import HireSettings, BlockedHireDate

# Import model factories as specified by the user
from hire.tests.test_helpers.model_factories import (
    create_hire_settings,
    create_temp_hire_booking,
    create_motorcycle,
    create_hire_booking,
)


class BikeChoiceViewTests(TestCase):
    """
    Tests for the BikeChoiceView (Step 2 of the hire booking process).
    This view displays available motorcycles based on dates and license status
    from a temporary booking.
    """

    def setUp(self):
        """
        Set up common data for tests:
        - A HireSettings instance.
        - Several Motorcycle instances with different engine sizes and rates.
        """
        self.client = Client()
        self.bike_choice_url = reverse('hire:step2_choose_bike')

        # Ensure HireSettings exists for validations
        self.hire_settings = create_hire_settings(
            minimum_hire_duration_hours=1,
            default_daily_rate=Decimal('50.00') # Set a default daily rate for consistency
        )

        # Create motorcycles for testing
        self.motorcycle_50cc = create_motorcycle(
            title="Scooter 50cc",
            model="Zoomer",
            engine_size=50,
            daily_hire_rate=Decimal('30.00'),
            is_available=True
        )
        self.motorcycle_250cc = create_motorcycle(
            title="Cruiser 250cc",
            model="Rebel",
            engine_size=250,
            daily_hire_rate=Decimal('70.00'),
            is_available=True
        )
        self.motorcycle_600cc = create_motorcycle(
            title="Sport Bike 600cc",
            model="CBR600",
            engine_size=600,
            daily_hire_rate=Decimal('120.00'),
            is_available=True
        )
        self.motorcycle_unavailable = create_motorcycle(
            title="Broken Bike",
            model="Broken",
            engine_size=125,
            daily_hire_rate=Decimal('40.00'),
            is_available=False # This bike should never show up
        )

        # Common booking dates for tests
        self.pickup_date = timezone.now().date() + datetime.timedelta(days=5)
        self.return_date = self.pickup_date + datetime.timedelta(days=2) # 3 days duration
        self.pickup_time = datetime.time(10, 0)
        self.return_time = datetime.time(16, 0)

    def _create_and_set_temp_booking_in_session(self, has_motorcycle_license=True,
                                                pickup_date=None, pickup_time=None,
                                                return_date=None, return_time=None):
        """
        Helper to create a TempHireBooking and set its ID/UUID in the session.
        """
        if pickup_date is None:
            pickup_date = self.pickup_date
        if pickup_time is None:
            pickup_time = self.pickup_time
        if return_date is None:
            return_date = self.return_date
        if return_time is None:
            return_time = self.return_time

        temp_booking = create_temp_hire_booking(
            pickup_date=pickup_date,
            pickup_time=pickup_time,
            return_date=return_date,
            return_time=return_time,
            has_motorcycle_license=has_motorcycle_license
        )
        session = self.client.session
        session['temp_booking_id'] = temp_booking.id
        session['temp_booking_uuid'] = str(temp_booking.session_uuid)
        session.save()
        return temp_booking

    # --- GET Request Tests ---

    def test_get_no_temp_booking_in_session(self):
        """
        Test GET request when no temp_booking_id is in the session.
        Should redirect or show an informative message and no motorcycles.
        """
        response = self.client.get(self.bike_choice_url)
        self.assertEqual(response.status_code, 200) # Should render the page, not redirect
        self.assertTemplateUsed(response, 'hire/step2_choose_bike.html')
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Please select your pickup and return dates" in str(m) for m in messages))
        self.assertIn('motorcycles', response.context)
        self.assertEqual(len(response.context['motorcycles']), 0)
        self.assertIsNone(response.context['temp_booking'])

    def test_get_invalid_temp_booking_id_uuid(self):
        """
        Test GET request with an invalid temp_booking_id/uuid in session.
        Should clear session and show an error message.
        """
        session = self.client.session
        session['temp_booking_id'] = 9999 # Non-existent ID
        session['temp_booking_uuid'] = str(uuid.uuid4()) # Random UUID
        session.save()

        response = self.client.get(self.bike_choice_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'hire/step2_choose_bike.html')
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Your previous booking details could not be found" in str(m) for m in messages))
        self.assertNotIn('temp_booking_id', self.client.session) # Session should be cleared
        self.assertNotIn('temp_booking_uuid', self.client.session)
        self.assertIsNone(response.context['temp_booking'])

    def test_get_valid_temp_booking_no_license(self):
        """
        Test GET request with a valid TempHireBooking, user has NO motorcycle license.
        Only motorcycles with engine_size <= 50cc should be displayed.
        """
        self._create_and_set_temp_booking_in_session(has_motorcycle_license=False)

        response = self.client.get(self.bike_choice_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'hire/step2_choose_bike.html')
        self.assertIn('motorcycles', response.context)
        motorcycles_in_context = [m['object'] for m in response.context['motorcycles']]

        self.assertIn(self.motorcycle_50cc, motorcycles_in_context)
        self.assertNotIn(self.motorcycle_250cc, motorcycles_in_context)
        self.assertNotIn(self.motorcycle_600cc, motorcycles_in_context)
        self.assertNotIn(self.motorcycle_unavailable, motorcycles_in_context) # Should always be excluded

        # Check calculated prices
        for bike_data in response.context['motorcycles']:
            if bike_data['object'] == self.motorcycle_50cc:
                # Duration is 3 days (pickup_date to return_date is 2 full days + part of third day)
                # (return_datetime - pickup_datetime).days + (1 if (return_datetime - pickup_datetime).seconds > 0 else 0)
                # 2 days + 1 day = 3 days
                expected_total_price = self.motorcycle_50cc.daily_hire_rate * 3
                self.assertEqual(bike_data['total_hire_price'], expected_total_price)

    def test_get_valid_temp_booking_with_license(self):
        """
        Test GET request with a valid TempHireBooking, user HAS motorcycle license.
        All available motorcycles should be displayed.
        """
        self._create_and_set_temp_booking_in_session(has_motorcycle_license=True)

        response = self.client.get(self.bike_choice_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'hire/step2_choose_bike.html')
        self.assertIn('motorcycles', response.context)
        motorcycles_in_context = [m['object'] for m in response.context['motorcycles']]

        self.assertIn(self.motorcycle_50cc, motorcycles_in_context)
        self.assertIn(self.motorcycle_250cc, motorcycles_in_context)
        self.assertIn(self.motorcycle_600cc, motorcycles_in_context)
        self.assertNotIn(self.motorcycle_unavailable, motorcycles_in_context)

        # Check calculated prices for a few bikes
        for bike_data in response.context['motorcycles']:
            if bike_data['object'] == self.motorcycle_250cc:
                expected_total_price = self.motorcycle_250cc.daily_hire_rate * 3
                self.assertEqual(bike_data['total_hire_price'], expected_total_price)
            if bike_data['object'] == self.motorcycle_600cc:
                expected_total_price = self.motorcycle_600cc.daily_hire_rate * 3
                self.assertEqual(bike_data['total_hire_price'], expected_total_price)

    def test_get_motorcycles_excluded_by_existing_hire_booking(self):
        """
        Test that motorcycles with existing HireBookings overlapping the period are excluded.
        """
        # Create a HireBooking that overlaps with the test period for motorcycle_250cc
        create_hire_booking(
            motorcycle=self.motorcycle_250cc,
            pickup_date=self.pickup_date,
            pickup_time=self.pickup_time,
            return_date=self.return_date,
            return_time=self.return_time
        )

        self._create_and_set_temp_booking_in_session(has_motorcycle_license=True)

        response = self.client.get(self.bike_choice_url)
        self.assertEqual(response.status_code, 200)
        motorcycles_in_context = [m['object'] for m in response.context['motorcycles']]

        self.assertIn(self.motorcycle_50cc, motorcycles_in_context)
        self.assertNotIn(self.motorcycle_250cc, motorcycles_in_context) # Should be excluded
        self.assertIn(self.motorcycle_600cc, motorcycles_in_context)

    def test_get_motorcycles_excluded_by_existing_temp_booking(self):
        """
        Test that motorcycles with existing TempHireBookings overlapping the period are excluded.
        This simulates another user having a bike in their temporary cart.
        """
        # Create another TempHireBooking that overlaps for motorcycle_600cc
        create_temp_hire_booking(
            motorcycle=self.motorcycle_600cc,
            pickup_date=self.pickup_date,
            pickup_time=self.pickup_time,
            return_date=self.return_date,
            return_time=self.return_time,
            has_motorcycle_license=True,
            session_uuid=uuid.uuid4() # Ensure it's a different session
        )

        self._create_and_set_temp_booking_in_session(has_motorcycle_license=True)

        response = self.client.get(self.bike_choice_url)
        self.assertEqual(response.status_code, 200)
        motorcycles_in_context = [m['object'] for m in response.context['motorcycles']]

        self.assertIn(self.motorcycle_50cc, motorcycles_in_context)
        self.assertIn(self.motorcycle_250cc, motorcycles_in_context)
        self.assertNotIn(self.motorcycle_600cc, motorcycles_in_context) # Should be excluded

    def test_get_motorcycles_sorting_low_to_high(self):
        """
        Test sorting of motorcycles by price from low to high.
        """
        self._create_and_set_temp_booking_in_session(has_motorcycle_license=True)
        # Expected order based on daily_hire_rate * 3 days:
        # 50cc (30*3=90), 250cc (70*3=210), 600cc (120*3=360)
        expected_order_ids = [self.motorcycle_50cc.id, self.motorcycle_250cc.id, self.motorcycle_600cc.id]

        response = self.client.get(self.bike_choice_url + '?order=price_low_to_high')
        self.assertEqual(response.status_code, 200)
        motorcycles_in_context = [m['object'] for m in response.context['motorcycles']]
        actual_order_ids = [m.id for m in motorcycles_in_context]

        self.assertEqual(actual_order_ids, expected_order_ids)
        self.assertEqual(response.context['current_order'], 'price_low_to_high')

    def test_get_motorcycles_sorting_high_to_low(self):
        """
        Test sorting of motorcycles by price from high to low.
        """
        self._create_and_set_temp_booking_in_session(has_motorcycle_license=True)
        # Expected order based on daily_hire_rate * 3 days:
        # 600cc (120*3=360), 250cc (70*3=210), 50cc (30*3=90)
        expected_order_ids = [self.motorcycle_600cc.id, self.motorcycle_250cc.id, self.motorcycle_50cc.id]

        response = self.client.get(self.bike_choice_url + '?order=price_high_to_low')
        self.assertEqual(response.status_code, 200)
        motorcycles_in_context = [m['object'] for m in response.context['motorcycles']]
        actual_order_ids = [m.id for m in motorcycles_in_context]

        self.assertEqual(actual_order_ids, expected_order_ids)
        self.assertEqual(response.context['current_order'], 'price_high_to_low')

    def test_get_motorcycles_pagination(self):
        """
        Test that pagination works correctly.
        """
        # Create more motorcycles to ensure multiple pages
        for i in range(10):
            create_motorcycle(
                title=f"Test Bike {i}",
                model=f"Model {i}",
                engine_size=150,
                daily_hire_rate=Decimal(f'55.{i}'),
                is_available=True
            )
        
        self._create_and_set_temp_booking_in_session(has_motorcycle_license=True)
        # Total motorcycles: 3 (from setup) + 10 (newly created) = 13
        # paginate_by is 9, so 2 pages expected

        # Request first page
        response = self.client.get(self.bike_choice_url + '?page=1')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_paginated'])
        self.assertEqual(len(response.context['motorcycles']), 9) # First page should have 9 bikes
        self.assertEqual(response.context['page_obj'].number, 1)

        # Request second page
        response = self.client.get(self.bike_choice_url + '?page=2')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_paginated'])
        self.assertEqual(len(response.context['motorcycles']), 4) # Second page should have 4 bikes (13 - 9)
        self.assertEqual(response.context['page_obj'].number, 2)

        # Request non-existent page
        response = self.client.get(self.bike_choice_url + '?page=99')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['motorcycles']), 4) # Should return last page
        self.assertEqual(response.context['page_obj'].number, 2)

    def test_abandoned_temp_hire_bookings_are_deleted(self):
        """
        Tests that TempHireBooking instances older than 2 hours are deleted
        when the BikeChoiceView is accessed.
        """
        # Create some TempHireBooking instances
        now = timezone.now()
        
        # Booking older than 2 hours, should be deleted
        old_booking_1 = create_temp_hire_booking(
            pickup_date=now.date(),
            pickup_time=now.time(),
            return_date=(now + timedelta(days=1)).date(),
            return_time=now.time(),
        )
        # Manually update updated_at directly in the database to bypass auto_now
        TempHireBooking.objects.filter(id=old_booking_1.id).update(
            created_at=now - timedelta(hours=2, minutes=5),
            updated_at=now - timedelta(hours=2, minutes=5)
        )

        # Another booking older than 2 hours, should be deleted
        old_booking_2 = create_temp_hire_booking(
            pickup_date=now.date(),
            pickup_time=now.time(),
            return_date=(now + timedelta(days=1)).date(),
            return_time=now.time(),
        )
        # Manually update updated_at directly in the database to bypass auto_now
        TempHireBooking.objects.filter(id=old_booking_2.id).update(
            created_at=now - timedelta(hours=3),
            updated_at=now - timedelta(hours=3)
        )

        # Booking more recent than 2 hours, should NOT be deleted
        recent_booking = create_temp_hire_booking(
            pickup_date=now.date(),
            pickup_time=now.time(),
            return_date=(now + timedelta(days=1)).date(),
            return_time=now.time(),
        )
        # Manually update updated_at directly in the database to bypass auto_now
        TempHireBooking.objects.filter(id=recent_booking.id).update(
            created_at=now - timedelta(hours=1),
            updated_at=now - timedelta(hours=1)
        )

        # Access the BikeChoiceView (this should trigger the cleanup)
        # We need a valid temp_booking in session for the view to proceed and trigger cleanup.
        # This will create a *new* temp booking, but the cleanup logic runs *before* it tries
        # to retrieve the session's temp booking.
        self._create_and_set_temp_booking_in_session(has_motorcycle_license=True) 
        response = self.client.get(self.bike_choice_url)
        self.assertEqual(response.status_code, 200) # Ensure the view rendered successfully

        # Check that the old bookings are deleted
        self.assertFalse(TempHireBooking.objects.filter(id=old_booking_1.id).exists())
        self.assertFalse(TempHireBooking.objects.filter(id=old_booking_2.id).exists())

        # Check that the recent booking still exists
        self.assertTrue(TempHireBooking.objects.filter(id=recent_booking.id).exists())

