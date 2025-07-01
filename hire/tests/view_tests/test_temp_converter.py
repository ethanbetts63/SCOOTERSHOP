                                        

from django.test import TestCase
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from unittest.mock import patch, MagicMock

                       
from hire.temp_hire_converter import convert_temp_to_hire_booking

        
from hire.models import (
    TempHireBooking,
    HireBooking,
    BookingAddOn,
    TempBookingAddOn,
    AddOn,
)
from payments.models import Payment
from inventory.models import Motorcycle
from hire.models.driver_profile import DriverProfile

                                                 
from hire.tests.test_helpers.model_factories import (
    create_temp_hire_booking,
    create_temp_booking_addon,
    create_addon,
    create_payment,
    create_motorcycle,
    create_driver_profile,
    create_hire_settings,
)

class TestConvertTempToHireBooking(TestCase):
    """
    Test suite for the convert_temp_to_hire_booking function,
    using django.test.TestCase.
    """

    def setUp(self):
        """
        Set up common data for tests.
        This method is called before each test function in this class.
        """
        create_hire_settings()                            
        self.motorcycle = create_motorcycle(daily_hire_rate=Decimal('100.00'), hourly_hire_rate=Decimal('20.00'))
        self.driver_profile = create_driver_profile(name="Test Driver")
        self.temp_booking = create_temp_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile,
            total_hire_price=Decimal('200.00'),
            total_addons_price=Decimal('0.00'),
            total_package_price=Decimal('0.00'),
            grand_total=Decimal('200.00'),
            deposit_amount=Decimal('50.00'),
            currency='AUD'
        )

    def test_convert_basic_booking_successful(self):
        """
        Test basic conversion without add-ons or an existing payment object.
        """
        temp_booking_id = self.temp_booking.id
        payment_method = 'online'
        booking_payment_status = 'paid'
        amount_paid = self.temp_booking.grand_total
        stripe_id = "pi_test123"

        hire_booking = convert_temp_to_hire_booking(
            temp_booking=self.temp_booking,
            payment_method=payment_method,
            booking_payment_status=booking_payment_status,
            amount_paid_on_booking=amount_paid,
            stripe_payment_intent_id=stripe_id
        )

                                                                  
        self.assertIsNotNone(hire_booking)
        self.assertIsInstance(hire_booking, HireBooking)
        self.assertEqual(hire_booking.motorcycle, self.motorcycle)
        self.assertEqual(hire_booking.driver_profile, self.driver_profile)
        self.assertEqual(hire_booking.package, self.temp_booking.package)
        self.assertEqual(hire_booking.total_hire_price, self.temp_booking.total_hire_price)
        self.assertEqual(hire_booking.total_addons_price, self.temp_booking.total_addons_price)
        self.assertEqual(hire_booking.total_package_price, self.temp_booking.total_package_price)
        self.assertEqual(hire_booking.grand_total, self.temp_booking.grand_total)
        self.assertEqual(hire_booking.pickup_date, self.temp_booking.pickup_date)
        self.assertEqual(hire_booking.pickup_time, self.temp_booking.pickup_time)
        self.assertEqual(hire_booking.return_date, self.temp_booking.return_date)
        self.assertEqual(hire_booking.return_time, self.temp_booking.return_time)
        self.assertEqual(hire_booking.is_international_booking, self.temp_booking.is_international_booking)
        self.assertEqual(hire_booking.booked_daily_rate, self.temp_booking.booked_daily_rate)
        self.assertEqual(hire_booking.booked_hourly_rate, self.temp_booking.booked_hourly_rate)
        self.assertEqual(hire_booking.deposit_amount, self.temp_booking.deposit_amount)
        self.assertEqual(hire_booking.currency, self.temp_booking.currency)

                                       
        self.assertEqual(hire_booking.amount_paid, amount_paid)
        self.assertEqual(hire_booking.payment_status, booking_payment_status)
        self.assertEqual(hire_booking.payment_method, payment_method)
        self.assertEqual(hire_booking.stripe_payment_intent_id, stripe_id)
        self.assertEqual(hire_booking.status, 'confirmed')

                                           
        with self.assertRaises(TempHireBooking.DoesNotExist):
            TempHireBooking.objects.get(id=temp_booking_id)

                                              
        self.assertEqual(BookingAddOn.objects.filter(booking=hire_booking).count(), 0)

    def test_convert_booking_with_addons_successful(self):
        """
        Test conversion when the TempHireBooking has associated add-ons.
        """
        addon1 = create_addon(name="Helmet", daily_cost=Decimal('10.00'))
        addon2 = create_addon(name="Jacket", daily_cost=Decimal('15.00'))
        temp_addon1 = create_temp_booking_addon(
            temp_booking=self.temp_booking,
            addon=addon1,
            quantity=1,
            booked_addon_price=Decimal('10.00')
        )
        temp_addon2 = create_temp_booking_addon(
            temp_booking=self.temp_booking,
            addon=addon2,
            quantity=2,
            booked_addon_price=Decimal('30.00')
        )
        self.temp_booking.total_addons_price = Decimal('40.00')
        self.temp_booking.grand_total += Decimal('40.00')
        self.temp_booking.save()

        temp_booking_id = self.temp_booking.id
        payment_method = 'in_store'
        booking_payment_status = 'pending_in_store'
        amount_paid = Decimal('0.00')

        hire_booking = convert_temp_to_hire_booking(
            temp_booking=self.temp_booking,
            payment_method=payment_method,
            booking_payment_status=booking_payment_status,
            amount_paid_on_booking=amount_paid
        )

        self.assertIsNotNone(hire_booking)
        self.assertEqual(hire_booking.total_addons_price, Decimal('40.00'))
                                                                 
        self.assertEqual(hire_booking.grand_total, Decimal('240.00'))                           

                                          
        self.assertEqual(BookingAddOn.objects.filter(booking=hire_booking).count(), 2)
        ba1 = BookingAddOn.objects.get(booking=hire_booking, addon=addon1)
        ba2 = BookingAddOn.objects.get(booking=hire_booking, addon=addon2)
        self.assertEqual(ba1.quantity, temp_addon1.quantity)
        self.assertEqual(ba1.booked_addon_price, temp_addon1.booked_addon_price)
        self.assertEqual(ba2.quantity, temp_addon2.quantity)
        self.assertEqual(ba2.booked_addon_price, temp_addon2.booked_addon_price)

                                                                      
        with self.assertRaises(TempHireBooking.DoesNotExist):
            TempHireBooking.objects.get(id=temp_booking_id)
        self.assertEqual(TempBookingAddOn.objects.filter(temp_booking_id=temp_booking_id).count(), 0)

    def test_convert_booking_with_existing_payment_object(self):
        """
        Test conversion when an existing Payment object is provided.
        """
                                                                                  
                                                                                    
                                                                  
        payment_obj = create_payment(
            amount=self.temp_booking.grand_total,
            status='authorized'
                                                                                                        
        )
        payment_obj.temp_hire_booking = self.temp_booking
                                                                                  
                                                                                          
        payment_obj.driver_profile = None
        payment_obj.save()

        payment_obj_id = payment_obj.id                           
        temp_booking_id = self.temp_booking.id
        payment_method = 'online'
        booking_payment_status = 'paid'
        amount_paid = self.temp_booking.grand_total

        hire_booking = convert_temp_to_hire_booking(
            temp_booking=self.temp_booking,
            payment_method=payment_method,
            booking_payment_status=booking_payment_status,
            amount_paid_on_booking=amount_paid,
            payment_obj=payment_obj
        )

        self.assertIsNotNone(hire_booking)

                                          
        updated_payment_obj = Payment.objects.get(id=payment_obj_id)
        self.assertEqual(updated_payment_obj.hire_booking, hire_booking)
        self.assertIsNone(updated_payment_obj.temp_hire_booking)
        self.assertEqual(updated_payment_obj.driver_profile, hire_booking.driver_profile)                    

                                           
        with self.assertRaises(TempHireBooking.DoesNotExist):
            TempHireBooking.objects.get(id=temp_booking_id)

    def test_deposit_amount_copied_correctly_when_none(self):
        """
        Test deposit_amount is set to 0.00 if None in TempHireBooking.
        """
        self.temp_booking.deposit_amount = None
        self.temp_booking.save()

        hire_booking = convert_temp_to_hire_booking(
            temp_booking=self.temp_booking,
            payment_method='online',
            booking_payment_status='paid',
            amount_paid_on_booking=self.temp_booking.grand_total                                       
        )
        self.assertEqual(hire_booking.deposit_amount, Decimal('0.00'))

    def test_deposit_amount_copied_correctly_when_set(self):
        """
        Test deposit_amount is copied if set in TempHireBooking.
        """
        expected_deposit = Decimal('75.50')
        self.temp_booking.deposit_amount = expected_deposit
        self.temp_booking.save()

        hire_booking = convert_temp_to_hire_booking(
            temp_booking=self.temp_booking,
            payment_method='online',
            booking_payment_status='deposit_paid',                 
            amount_paid_on_booking=expected_deposit                             
        )
        self.assertEqual(hire_booking.deposit_amount, expected_deposit)

    @patch('hire.temp_hire_converter.BookingAddOn.objects.create', side_effect=Exception("Simulated DB error"))
    def test_conversion_rolls_back_on_error_during_addon_copy(self, mock_create_addon):
        """
        Test that the transaction rolls back on error during add-on copy.
        """
        temp_booking_id = self.temp_booking.id
        addon1 = create_addon(name="Faulty Addon")
        create_temp_booking_addon(temp_booking=self.temp_booking, addon=addon1, quantity=1)

                                                    
        with self.assertRaises(Exception) as cm:
            convert_temp_to_hire_booking(
                temp_booking=self.temp_booking,
                payment_method='online',
                booking_payment_status='paid',
                amount_paid_on_booking=self.temp_booking.grand_total
            )
        self.assertEqual(str(cm.exception), "Simulated DB error")

                                                                       
        self.assertTrue(TempHireBooking.objects.filter(id=temp_booking_id).exists())

                                                       
        self.assertFalse(HireBooking.objects.filter(
            motorcycle=self.temp_booking.motorcycle,
            pickup_date=self.temp_booking.pickup_date
        ).exists())

                                              
        self.assertTrue(TempBookingAddOn.objects.filter(temp_booking_id=temp_booking_id).exists())

    def test_all_fields_copied_correctly(self):
        """
        A more comprehensive check that all relevant fields are copied.
        """
                                                                      
        self.temp_booking.total_hire_price = Decimal('250.75')
        self.temp_booking.total_addons_price = Decimal('30.50')
        self.temp_booking.total_package_price = Decimal('50.25')
        self.temp_booking.grand_total = Decimal('331.50')                         
        self.temp_booking.is_international_booking = True
        self.temp_booking.booked_daily_rate = Decimal('125.37')
        self.temp_booking.booked_hourly_rate = Decimal('25.15')
        self.temp_booking.deposit_amount = Decimal('100.00')
        self.temp_booking.currency = 'USD'
        self.temp_booking.save()

        payment_method = 'card'
        booking_payment_status = 'deposit_paid'
        amount_paid = self.temp_booking.deposit_amount                             
        stripe_id = "pi_anotherTest789"

        hire_booking = convert_temp_to_hire_booking(
            temp_booking=self.temp_booking,
            payment_method=payment_method,
            booking_payment_status=booking_payment_status,
            amount_paid_on_booking=amount_paid,
            stripe_payment_intent_id=stripe_id
        )

        self.assertEqual(hire_booking.motorcycle, self.temp_booking.motorcycle)
        self.assertEqual(hire_booking.driver_profile, self.temp_booking.driver_profile)
        self.assertEqual(hire_booking.package, self.temp_booking.package)
        self.assertEqual(hire_booking.total_hire_price, self.temp_booking.total_hire_price)
        self.assertEqual(hire_booking.total_addons_price, self.temp_booking.total_addons_price)
        self.assertEqual(hire_booking.total_package_price, self.temp_booking.total_package_price)
        self.assertEqual(hire_booking.grand_total, self.temp_booking.grand_total)
        self.assertEqual(hire_booking.pickup_date, self.temp_booking.pickup_date)
        self.assertEqual(hire_booking.pickup_time, self.temp_booking.pickup_time)
        self.assertEqual(hire_booking.return_date, self.temp_booking.return_date)
        self.assertEqual(hire_booking.return_time, self.temp_booking.return_time)
        self.assertEqual(hire_booking.is_international_booking, self.temp_booking.is_international_booking)
        self.assertEqual(hire_booking.booked_daily_rate, self.temp_booking.booked_daily_rate)
        self.assertEqual(hire_booking.booked_hourly_rate, self.temp_booking.booked_hourly_rate)
        self.assertEqual(hire_booking.deposit_amount, self.temp_booking.deposit_amount)
        self.assertEqual(hire_booking.currency, self.temp_booking.currency)
        self.assertEqual(hire_booking.amount_paid, amount_paid)
        self.assertEqual(hire_booking.payment_status, booking_payment_status)
        self.assertEqual(hire_booking.payment_method, payment_method)
        self.assertEqual(hire_booking.stripe_payment_intent_id, stripe_id)
        self.assertEqual(hire_booking.status, 'confirmed')

