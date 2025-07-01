                                              

from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError

                        
from hire.tests.test_helpers.model_factories import (
    create_hire_booking,
    create_addon,
    create_booking_addon,
    create_motorcycle,
    create_driver_profile,
    create_hire_settings,                              
)

                                                                  
from hire.hire_pricing import calculate_addon_price
import datetime
from django.utils import timezone


class BookingAddOnModelTest(TestCase):
    """
    Unit tests for the BookingAddOn model.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods.
        """
                                                          
        cls.hire_settings = create_hire_settings(
            hire_pricing_strategy='24_hour_customer_friendly',                         
            excess_hours_margin=2                       
        )

        cls.motorcycle = create_motorcycle()
        
                                                                                                   
        cls.pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        cls.pickup_time = datetime.time(10, 0)
        cls.return_date = cls.pickup_date + datetime.timedelta(days=2)                                     
        cls.return_time = datetime.time(16, 0)                             

        cls.driver_profile = create_driver_profile()
        cls.booking = create_hire_booking(
            motorcycle=cls.motorcycle,
            driver_profile=cls.driver_profile,
            pickup_date=cls.pickup_date,
            pickup_time=cls.pickup_time,
            return_date=cls.return_date,
            return_time=cls.return_time,
            grand_total=Decimal('100.00')                                                                    
        )
                                                       
        cls.available_addon = create_addon(name="Available AddOn", daily_cost=Decimal('10.00'), hourly_cost=Decimal('2.00'), is_available=True)
        cls.unavailable_addon = create_addon(name="Unavailable AddOn", daily_cost=Decimal('20.00'), hourly_cost=Decimal('4.00'), is_available=False)

                                                                                
                                                               
        cls.expected_addon_price_per_unit_for_default_booking = calculate_addon_price(
            addon_instance=cls.available_addon,
            quantity=1,                              
            pickup_date=cls.booking.pickup_date,
            return_date=cls.booking.return_date,
            pickup_time=cls.booking.pickup_time,
            return_time=cls.booking.return_time,
            hire_settings=cls.hire_settings
        )

    def test_create_basic_booking_addon(self):
        """
        Test that a basic BookingAddOn instance can be created.
        """
                                                                                       
                                                                                   
                                                                                
                                                                               
        quantity = 2
        expected_booked_price = self.expected_addon_price_per_unit_for_default_booking * quantity
        booking_addon = create_booking_addon(
            booking=self.booking,
            addon=self.available_addon,
            quantity=quantity,
            booked_addon_price=expected_booked_price                                
        )
        self.assertIsNotNone(booking_addon.pk)
        self.assertEqual(booking_addon.booking, self.booking)
        self.assertEqual(booking_addon.addon, self.available_addon)
        self.assertEqual(booking_addon.quantity, quantity)
        self.assertEqual(booking_addon.booked_addon_price, expected_booked_price)

    def test_str_method(self):
        """
        Test the __str__ method of BookingAddOn.
        """
        booking_addon = create_booking_addon(
            booking=self.booking,
            addon=self.available_addon,
            quantity=3,
            booked_addon_price=self.expected_addon_price_per_unit_for_default_booking * 3
        )
        expected_str = f"3 x {self.available_addon.name} for Booking {self.booking.booking_reference}"
        self.assertEqual(str(booking_addon), expected_str)

    def test_unique_together_constraint(self):
        """
        Test that unique_together constraint (booking, addon) prevents duplicates.
        """
        create_booking_addon(
            booking=self.booking,
            addon=self.available_addon,
            quantity=1,
            booked_addon_price=self.expected_addon_price_per_unit_for_default_booking * 1
        )
        with self.assertRaises(IntegrityError):
            create_booking_addon(
                booking=self.booking,
                addon=self.available_addon,                              
                quantity=2,                                         
                booked_addon_price=self.expected_addon_price_per_unit_for_default_booking * 2
            )

                                  

    def test_clean_unavailable_addon_raises_error(self):
        """
        Test that clean() raises ValidationError if the selected add-on is not available.
        """
        booking_addon = create_booking_addon(
            booking=self.booking,
            addon=self.unavailable_addon,                              
            quantity=1,
                                                                             
            booked_addon_price=Decimal('0.00') 
        )
        with self.assertRaises(ValidationError) as cm:
            booking_addon.clean()
        self.assertIn('addon', cm.exception.message_dict)
        self.assertEqual(
            cm.exception.message_dict['addon'][0],
            f"The add-on '{self.unavailable_addon.name}' is currently not available."
        )

    def test_clean_booked_addon_price_mismatch_raises_error(self):
        """
        Test that clean() raises ValidationError if booked_addon_price does not match
        the calculated total price.
        """
                                                                                          
                                                                                                            
        quantity = 1
        incorrect_booked_price = self.expected_addon_price_per_unit_for_default_booking * quantity + Decimal('0.01')           
        
        booking_addon = create_booking_addon(
            booking=self.booking,
            addon=self.available_addon,
            quantity=quantity,
            booked_addon_price=incorrect_booked_price 
        )
        with self.assertRaises(ValidationError) as cm:
            booking_addon.clean()
        self.assertIn('booked_addon_price', cm.exception.message_dict)
        
                                                                                                    
        expected_calculated_total_price = self.expected_addon_price_per_unit_for_default_booking * quantity
        
        self.assertEqual(
            cm.exception.message_dict['booked_addon_price'][0],
            f"Booked add-on price ({incorrect_booked_price}) must match the calculated total price "
            f"({expected_calculated_total_price}) for {quantity} unit(s) of {self.available_addon.name}."
        )

    def test_clean_valid_booking_addon_passes(self):
        """
        Test that a valid BookingAddOn instance passes clean() without errors.
        """
                                                                                    
        quantity = 1
        correct_booked_price = self.expected_addon_price_per_unit_for_default_booking * quantity
        
        booking_addon = create_booking_addon(
            booking=self.booking,
            addon=self.available_addon,
            quantity=quantity,
            booked_addon_price=correct_booked_price                                 
        )
        try:
            booking_addon.clean()
        except ValidationError:
            self.fail("ValidationError raised unexpectedly for a valid BookingAddOn.")

