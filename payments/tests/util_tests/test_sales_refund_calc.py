                                                     

from django.test import TestCase
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from unittest.mock import MagicMock

                                  
from payments.utils.sales_refund_calc import calculate_sales_refund_amount

                                         
from payments.tests.test_helpers.model_factories import SalesBookingFactory, PaymentFactory, RefundPolicySettingsFactory

class SalesRefundCalcTests(TestCase):
    """
    Tests for the calculate_sales_refund_amount function in payments.utils.sales_refund_calc.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up test data that will be used across all test methods in this class.
        We create a single RefundPolicySettings instance as it's a singleton,
        and define common refund policy snapshots for easier testing.
        """
        cls.refund_policy_settings = RefundPolicySettingsFactory()

                                                                        
                                                                                                     
                                                                                     
        cls.full_refund_enabled_grace_period_policy = {
            'sales_enable_deposit_refund': True,
            'sales_enable_deposit_refund_grace_period': True,
            'sales_deposit_refund_grace_period_hours': 24,                        
        }

        cls.full_refund_enabled_no_grace_period_policy = {
            'sales_enable_deposit_refund': True,
            'sales_enable_deposit_refund_grace_period': False,
            'sales_deposit_refund_grace_period_hours': 0,                                        
        }

        cls.no_refund_disabled_policy = {
            'sales_enable_deposit_refund': False,
            'sales_enable_deposit_refund_grace_period': True,             
            'sales_deposit_refund_grace_period_hours': 24,                
        }

    def _create_booking_with_payment(self, amount_paid, created_at_offset_hours=0, refund_policy_snapshot=None):
        """
        Helper to create a SalesBooking and an associated Payment.
        `created_at_offset_hours`: How many hours in the past the booking was created.
        """
                                                                   
        payment = PaymentFactory(amount=amount_paid, status='succeeded')
        if refund_policy_snapshot:
                                                                                                            
            processed_snapshot = {k: str(v) if isinstance(v, Decimal) else v for k, v in refund_policy_snapshot.items()}
            payment.refund_policy_snapshot = processed_snapshot
        else:
            payment.refund_policy_snapshot = {}
        payment.save()

                                                                                                                 
        booking = SalesBookingFactory(
            payment=payment,
            amount_paid=amount_paid,
                                                                                     
                                                                                         
            booking_status='confirmed',
            payment_status='deposit_paid' if amount_paid > 0 else 'unpaid',
        )

                                                                                               
                                                                     
        booking.created_at = timezone.now() - timedelta(hours=created_at_offset_hours)
        booking.save()

        return booking, payment

                                                   

    def test_full_refund_within_grace_period(self):
        """
        Tests full refund when deposit refunds are enabled, grace period is enabled,
        and cancellation occurs within the grace period.
        """
                                                                
        booking, payment = self._create_booking_with_payment(
            amount_paid=Decimal('100.00'),
            created_at_offset_hours=12,
            refund_policy_snapshot=self.full_refund_enabled_grace_period_policy
        )
        cancellation_datetime = timezone.now()                   

        result = calculate_sales_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('100.00'))
        self.assertEqual(result['policy_applied'], "Full Refund Policy (Within 24 hour grace period)")
        self.assertAlmostEqual(result['time_since_booking_creation_hours'], 12.0, places=1)
        self.assertIn("Cancellation occurred 12.00 hours after booking creation.", result['details'])

    def test_no_refund_outside_grace_period(self):
        """
        Tests no refund when deposit refunds are enabled, grace period is enabled,
        but cancellation occurs outside the grace period.
        """
                                                                
        booking, payment = self._create_booking_with_payment(
            amount_paid=Decimal('100.00'),
            created_at_offset_hours=30,
            refund_policy_snapshot=self.full_refund_enabled_grace_period_policy
        )
        cancellation_datetime = timezone.now()

        result = calculate_sales_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('0.00'))
        self.assertEqual(result['policy_applied'], "No Refund Policy (Grace Period Expired)")
        self.assertAlmostEqual(result['time_since_booking_creation_hours'], 30.0, places=1)
        self.assertIn("Cancellation occurred 30.00 hours after booking creation.", result['details'])

    def test_full_refund_grace_period_disabled(self):
        """
        Tests full refund when deposit refunds are enabled but grace period is disabled.
        Should always result in a full refund.
        """
                                                                    
        booking, payment = self._create_booking_with_payment(
            amount_paid=Decimal('100.00'),
            created_at_offset_hours=50,
            refund_policy_snapshot=self.full_refund_enabled_no_grace_period_policy
        )
        cancellation_datetime = timezone.now()

        result = calculate_sales_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('100.00'))
        self.assertEqual(result['policy_applied'], "Full Refund Policy (Grace Period Disabled)")
        self.assertAlmostEqual(result['time_since_booking_creation_hours'], 50.0, places=1)
        self.assertIn("Cancellation occurred 50.00 hours after booking creation.", result['details'])

    def test_no_refund_deposit_refund_disabled(self):
        """
        Tests no refund when deposit refunds are entirely disabled.
        """
                                                                        
        booking, payment = self._create_booking_with_payment(
            amount_paid=Decimal('100.00'),
            created_at_offset_hours=10,
            refund_policy_snapshot=self.no_refund_disabled_policy
        )
        cancellation_datetime = timezone.now()

        result = calculate_sales_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('0.00'))
        self.assertEqual(result['policy_applied'], "No Refund Policy (Refunds Disabled)")
        self.assertAlmostEqual(result['time_since_booking_creation_hours'], 10.0, places=1)
        self.assertIn("Cancellation occurred 10.00 hours after booking creation.", result['details'])

    def test_no_refund_policy_snapshot(self):
        """
        Tests behavior when refund_policy_snapshot is missing or empty.
        Should result in no refund and appropriate details.
        """
        booking, payment = self._create_booking_with_payment(
            amount_paid=Decimal('100.00'),
            refund_policy_snapshot={}                 
        )
        result = calculate_sales_refund_amount(booking, {}, timezone.now())                           

        self.assertEqual(result['entitled_amount'], Decimal('0.00'))
        self.assertEqual(result['details'], "No refund policy snapshot available for this booking's payment.")
        self.assertEqual(result['policy_applied'], 'N/A')
        self.assertEqual(result['time_since_booking_creation_hours'], 'N/A')

    def test_zero_amount_paid(self):
        """
        Tests calculation when the amount paid for the booking is zero.
        Should always result in a zero refund.
        """
        booking, payment = self._create_booking_with_payment(
            amount_paid=Decimal('0.00'),
            created_at_offset_hours=1,
            refund_policy_snapshot=self.full_refund_enabled_grace_period_policy
        )
        cancellation_datetime = timezone.now()

        result = calculate_sales_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('0.00'))
        self.assertIn("Calculated: 0.00.", result['details'])
                                                                                 

    def test_custom_cancellation_datetime(self):
        """
        Tests that a custom cancellation_datetime is used correctly for time difference calculation.
        """
                                        
        booking, payment = self._create_booking_with_payment(
            amount_paid=Decimal('100.00'),
            created_at_offset_hours=0,
            refund_policy_snapshot=self.full_refund_enabled_grace_period_policy
        )

                                                                   
        custom_cancellation_datetime = booking.created_at + timedelta(hours=25)

        result = calculate_sales_refund_amount(booking, payment.refund_policy_snapshot, custom_cancellation_datetime)

                                                                               
        self.assertEqual(result['entitled_amount'], Decimal('0.00'))
        self.assertEqual(result['policy_applied'], "No Refund Policy (Grace Period Expired)")
        self.assertAlmostEqual(result['time_since_booking_creation_hours'], 25.0, places=1)
        self.assertIn("Cancellation occurred 25.00 hours after booking creation.", result['details'])

    def test_exact_grace_period_boundary(self):
        """
        Tests cancellation exactly on the grace period boundary (e.g., 24 hours exactly).
        Should still be a full refund as it's <= grace_period_hours.
        """
        policy = self.full_refund_enabled_grace_period_policy.copy()
        policy['sales_deposit_refund_grace_period_hours'] = 24

        booking, payment = self._create_booking_with_payment(
            amount_paid=Decimal('100.00'),
            created_at_offset_hours=0,                                  
            refund_policy_snapshot=policy
        )
                                                      
        cancellation_datetime = booking.created_at + timedelta(hours=24)

        result = calculate_sales_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('100.00'))
        self.assertEqual(result['policy_applied'], "Full Refund Policy (Within 24 hour grace period)")
        self.assertAlmostEqual(result['time_since_booking_creation_hours'], 24.0, places=1)
        self.assertIn("Cancellation occurred 24.00 hours after booking creation.", result['details'])

    def test_just_after_grace_period_boundary(self):
        """
        Tests cancellation just after the grace period boundary (e.g., 24 hours and 1 minute).
        Should result in no refund.
        """
        policy = self.full_refund_enabled_grace_period_policy.copy()
        policy['sales_deposit_refund_grace_period_hours'] = 24

        booking, payment = self._create_booking_with_payment(
            amount_paid=Decimal('100.00'),
            created_at_offset_hours=0,
            refund_policy_snapshot=policy
        )
                                                           
        cancellation_datetime = booking.created_at + timedelta(hours=24, minutes=1)

        result = calculate_sales_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('0.00'))
        self.assertEqual(result['policy_applied'], "No Refund Policy (Grace Period Expired)")
                                                           
        self.assertTrue(result['time_since_booking_creation_hours'] > 24.0)
        self.assertIn("Cancellation occurred", result['details'])

    def test_negative_time_difference_cancellation_before_creation(self):
        """
        Tests the edge case where cancellation_datetime is before booking.created_at.
        Should result in a full refund as `time_since_booking_creation_hours` would be negative,
        satisfying `time_since_booking_creation_hours <= grace_period_hours`.
        The `max(Decimal('0.00'), ...)` line also handles ensuring the refund is not negative.
        """
        policy = self.full_refund_enabled_grace_period_policy.copy()
        policy['sales_deposit_refund_grace_period_hours'] = 24

                                                                                                       
                                                                                          
                                                                                                   
                                                                                                    

                                                                                                          
        fixed_now = timezone.make_aware(datetime(2025, 1, 1, 10, 0, 0))

                                      
        booking, payment = self._create_booking_with_payment(
            amount_paid=Decimal('100.00'),
            created_at_offset_hours=0,                                                                  
            refund_policy_snapshot=policy
        )
                                                                                
        booking.created_at = fixed_now + timedelta(hours=5)                                              
        booking.save()

                                                                               
        cancellation_datetime = fixed_now

        result = calculate_sales_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('100.00'))
        self.assertEqual(result['policy_applied'], "Full Refund Policy (Within 24 hour grace period)")
                                                                       
        self.assertLess(result['time_since_booking_creation_hours'], 0)
        self.assertIn("Cancellation occurred", result['details'])
