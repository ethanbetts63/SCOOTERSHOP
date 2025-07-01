                                                    

from django.test import TestCase
from decimal import Decimal
                                                                                                  
from datetime import datetime, date, time, timedelta
from django.utils import timezone
from unittest.mock import MagicMock

                   
from payments.utils.hire_refund_calc import calculate_hire_refund_amount
from payments.tests.test_helpers.model_factories import HireBookingFactory, PaymentFactory, RefundPolicySettingsFactory

class HireRefundCalcTests(TestCase):
    """
    Tests for the calculate_hire_refund_amount function in payments.hire_refund_calc.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up test data that will be used across all test methods in this class.
        We create a single RefundPolicySettings instance as it's a singleton.
        """
        cls.refund_policy_settings = RefundPolicySettingsFactory()

                                                                  
                                                                  
        cls.full_payment_policy_snapshot = {
            'deposit_enabled': False,
            'cancellation_upfront_full_refund_days': 7,
            'cancellation_upfront_partial_refund_days': 3,
            'cancellation_upfront_partial_refund_percentage': str(Decimal('50.00')),                    
            'cancellation_upfront_minimal_refund_days': 1,
            'cancellation_upfront_minimal_refund_percentage': str(Decimal('10.00')),                    
        }

        cls.deposit_payment_policy_snapshot = {
            'deposit_enabled': True,
            'cancellation_deposit_full_refund_days': 10,
            'cancellation_deposit_partial_refund_days': 5,
            'cancellation_deposit_partial_refund_percentage': str(Decimal('75.00')),                    
            'cancellation_deposit_minimal_refund_days': 2,
            'cancellation_deposit_minimal_refund_percentage': str(Decimal('20.00')),                    
        }

    def _create_booking_with_payment(self, total_amount, payment_method, payment_status=None, pickup_date_offset_days=10, refund_policy_snapshot=None):
        """
        Helper to create a HireBooking and an associated Payment.
        """
                                         
        payment = PaymentFactory(amount=total_amount, status='succeeded')

                                                                                               
        if refund_policy_snapshot:
            processed_snapshot = {k: str(v) if isinstance(v, Decimal) else v for k, v in refund_policy_snapshot.items()}
            payment.refund_policy_snapshot = processed_snapshot
        else:
            payment.refund_policy_snapshot = {}                                               
        payment.save()                                               

                                       
                                                               
        pickup_date = timezone.now().date() + timedelta(days=pickup_date_offset_days)
        pickup_time = time(10, 0)                                    

        booking = HireBookingFactory(
            payment=payment,
            payment_method=payment_method,
            payment_status=payment_status if payment_status else 'paid' if payment_method == 'online_full' else 'deposit_paid',
            grand_total=total_amount,                                                                        
            amount_paid=total_amount,
            pickup_date=pickup_date,
            pickup_time=pickup_time,
            return_date=pickup_date + timedelta(days=2),                        
            status='confirmed',
        )

        return booking, payment


                                                        

    def test_full_refund_full_payment(self):
        """
        Tests full refund for a full payment when cancelled well in advance.
        """
        cancellation_datetime = timezone.now()
                                                                  
                                                                          
                                                    
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('500.00'),
            payment_method='online_full',
            pickup_date_offset_days=9,                                                    
            refund_policy_snapshot=self.full_payment_policy_snapshot
        )

        result = calculate_hire_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('500.00'))
        self.assertEqual(result['policy_applied'], "Upfront Payment Policy: Full Refund Policy")
        self.assertIn("Cancellation 8 days before pickup.", result['details'])
        self.assertEqual(result['days_before_pickup'], 8)

    def test_partial_refund_full_payment(self):
        """
        Tests partial refund for a full payment when cancelled within partial refund window.
        """
        cancellation_datetime = timezone.now()
                                                                     
                                                                          
                                                    
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('500.00'),
            payment_method='online_full',
            pickup_date_offset_days=5,                                                    
            refund_policy_snapshot=self.full_payment_policy_snapshot
        )

        result = calculate_hire_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        expected_refund = (Decimal('500.00') * Decimal('50.00')) / Decimal('100.00')
        self.assertEqual(result['entitled_amount'], expected_refund)
        self.assertEqual(result['policy_applied'], "Upfront Payment Policy: Partial Refund Policy (50.00%)")
        self.assertIn("Cancellation 4 days before pickup.", result['details'])
        self.assertEqual(result['days_before_pickup'], 4)

    def test_minimal_refund_full_payment(self):
        """
        Tests minimal refund for a full payment when cancelled within minimal refund window.
        """
        cancellation_datetime = timezone.now()
                                                                    
                                                                          
                                                    
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('500.00'),
            payment_method='online_full',
            pickup_date_offset_days=3,                                                    
            refund_policy_snapshot=self.full_payment_policy_snapshot
        )

        result = calculate_hire_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        expected_refund = (Decimal('500.00') * Decimal('10.00')) / Decimal('100.00')
        self.assertEqual(result['entitled_amount'], expected_refund)
        self.assertEqual(result['policy_applied'], "Upfront Payment Policy: Minimal Refund Policy (10.00%)")
        self.assertIn("Cancellation 2 days before pickup.", result['details'])
        self.assertEqual(result['days_before_pickup'], 2)

    def test_no_refund_full_payment_too_close(self):
        """
        Tests no refund for a full payment when cancelled too close to pickup (less than minimal days).
        """
        cancellation_datetime = timezone.now()
                                                                               
                                                                          
                                                               
                                                                                          
                                                                                  
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('500.00'),
            payment_method='online_full',
            pickup_date_offset_days=1,                                                    
            refund_policy_snapshot=self.full_payment_policy_snapshot
        )

        result = calculate_hire_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('0.00'))
        self.assertEqual(result['policy_applied'], "Upfront Payment Policy: No Refund Policy (Too close to pickup or after pickup)")
        self.assertIn("Cancellation 0 days before pickup.", result['details'])
        self.assertEqual(result['days_before_pickup'], 0)

    def test_no_refund_full_payment_after_pickup(self):
        """
        Tests no refund for a full payment when cancelled after the pickup time.
        """
                                      
        pickup_date = timezone.now().date() - timedelta(days=1)
                                                     
        cancellation_datetime = timezone.now()

        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('500.00'),
            payment_method='online_full',
            pickup_date_offset_days=-1,                                                          
            refund_policy_snapshot=self.full_payment_policy_snapshot
        )
                                                                
        booking.pickup_date = pickup_date
        booking.save()

                                                                     
                                                                
        pickup_datetime = timezone.make_aware(datetime.combine(booking.pickup_date, booking.pickup_time))
        time_difference = pickup_datetime - cancellation_datetime
        days_in_advance = time_difference.days


        result = calculate_hire_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('0.00'))
        self.assertEqual(result['policy_applied'], "Upfront Payment Policy: No Refund Policy (Too close to pickup or after pickup)")
                                                                   
        self.assertIn(f"Cancellation {days_in_advance} days before pickup.", result['details'])
        self.assertEqual(result['days_before_pickup'], days_in_advance)                   


                                                              

    def test_full_refund_deposit_payment(self):
        """
        Tests full refund for a deposit payment when cancelled well in advance.
        """
        cancellation_datetime = timezone.now()
                                                                                
                                                                      
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('100.00'),                 
            payment_method='online_deposit',
            payment_status='deposit_paid',
            pickup_date_offset_days=12,                        
            refund_policy_snapshot=self.deposit_payment_policy_snapshot
        )

        result = calculate_hire_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('100.00'))
        self.assertEqual(result['policy_applied'], "Deposit Payment Policy: Full Refund Policy")
        self.assertIn("Cancellation 11 days before pickup.", result['details'])
        self.assertEqual(result['days_before_pickup'], 11)

    def test_partial_refund_deposit_payment(self):
        """
        Tests partial refund for a deposit payment when cancelled within partial refund window.
        """
        cancellation_datetime = timezone.now()
                                                                                 
                                                                    
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('100.00'),
            payment_method='online_deposit',
            payment_status='deposit_paid',
            pickup_date_offset_days=7,                      
            refund_policy_snapshot=self.deposit_payment_policy_snapshot
        )

        result = calculate_hire_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        expected_refund = (Decimal('100.00') * Decimal('75.00')) / Decimal('100.00')
        self.assertEqual(result['entitled_amount'], expected_refund)
        self.assertEqual(result['policy_applied'], "Deposit Payment Policy: Partial Refund Policy (75.00%)")
        self.assertIn("Cancellation 6 days before pickup.", result['details'])
        self.assertEqual(result['days_before_pickup'], 6)

    def test_minimal_refund_deposit_payment(self):
        """
        Tests minimal refund for a deposit payment when cancelled within minimal refund window.
        """
        cancellation_datetime = timezone.now()
                                                                                 
                                                                    
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('100.00'),
            payment_method='online_deposit',
            payment_status='deposit_paid',
            pickup_date_offset_days=4,                      
            refund_policy_snapshot=self.deposit_payment_policy_snapshot
        )

        result = calculate_hire_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        expected_refund = (Decimal('100.00') * Decimal('20.00')) / Decimal('100.00')
        self.assertEqual(result['entitled_amount'], expected_refund)
        self.assertEqual(result['policy_applied'], "Deposit Payment Policy: Minimal Refund Policy (20.00%)")
        self.assertIn("Cancellation 3 days before pickup.", result['details'])
        self.assertEqual(result['days_before_pickup'], 3)

    def test_no_refund_deposit_payment_too_close(self):
        """
        Tests no refund for a deposit payment when cancelled too close to pickup (less than minimal days).
        """
        cancellation_datetime = timezone.now()
                                                                                
                                                                   
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('100.00'),
            payment_method='online_deposit',
            payment_status='deposit_paid',
            pickup_date_offset_days=2,                      
            refund_policy_snapshot=self.deposit_payment_policy_snapshot
        )

        result = calculate_hire_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('0.00'))
        self.assertEqual(result['policy_applied'], "Deposit Payment Policy: No Refund Policy (Too close to pickup or after pickup)")
        self.assertIn("Cancellation 1 days before pickup.", result['details'])
        self.assertEqual(result['days_before_pickup'], 1)


                                            

    def test_no_refund_policy_snapshot(self):
        """
        Tests behavior when refund_policy_snapshot is missing or empty.
        """
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('500.00'),
            payment_method='online_full',
            refund_policy_snapshot={}                                  
        )
                                                                                          
        result = calculate_hire_refund_amount(booking, payment.refund_policy_snapshot, timezone.now())

        self.assertEqual(result['entitled_amount'], Decimal('0.00'))
        self.assertEqual(result['details'], "No refund policy snapshot available for this booking.")
        self.assertEqual(result['policy_applied'], 'N/A')
        self.assertEqual(result['days_before_pickup'], 'N/A')

    def test_manual_payment_method(self):
        """
        Tests behavior for payment methods that require manual refunds.
        """
        cancellation_datetime = timezone.now()
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('500.00'),
            payment_method='bank_transfer',                        
            pickup_date_offset_days=5,                                                                
            refund_policy_snapshot=self.full_payment_policy_snapshot
        )

        result = calculate_hire_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('0.00'))
                                                                                                                
        self.assertIn("No Refund Policy: Refund for 'bank_transfer' payment method is handled manually.", result['details'])
        self.assertEqual(result['policy_applied'], "Manual Refund Policy for bank_transfer")                         
        self.assertEqual(result['days_before_pickup'], 'N/A')

    def test_booking_without_payment_object(self):
        """
        Tests the case where a booking might not have a linked payment object.
        This shouldn't happen in a real scenario if payment.amount is used,
        but good for robustness. We mock the booking's payment attribute to be None.
        """
        cancellation_datetime = timezone.now()

                                                     
        mock_booking = MagicMock()
        mock_booking.payment = None                             
        mock_booking.payment_method = 'online_full'
        mock_booking.payment_status = 'paid'
                                       
        mock_booking.pickup_date = timezone.now().date() + timedelta(days=9)                           
        mock_booking.pickup_time = time(10, 0)
        mock_booking.get_payment_method_display.return_value = 'Online Full'


        result = calculate_hire_refund_amount(mock_booking, self.full_payment_policy_snapshot, cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('0.00'))
        self.assertIn("0.00 (100.00% of 0.00).", result['details'])                           
        self.assertIn("Cancellation 8 days before pickup.", result['details'])                             

    def test_custom_cancellation_datetime(self):
        """
        Tests that a custom cancellation_datetime is used correctly.
        """
                                                                                                  
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('500.00'),
            payment_method='online_full',
            pickup_date_offset_days=11,                        
            refund_policy_snapshot=self.full_payment_policy_snapshot
        )

                                                                                         
        pickup_datetime = timezone.make_aware(datetime.combine(booking.pickup_date, booking.pickup_time))
                                                                                
        custom_cancellation_datetime = pickup_datetime - timedelta(days=8, minutes=1)

        result = calculate_hire_refund_amount(booking, payment.refund_policy_snapshot, custom_cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('500.00'))
        self.assertEqual(result['policy_applied'], "Upfront Payment Policy: Full Refund Policy")
        self.assertEqual(result['days_before_pickup'], 8)                                        

    def test_exact_boundary_full_refund_days(self):
        """
        Tests cancellation exactly on the boundary for full refund.
        Should result in a full refund.
        """
                                                                          
                                                                       
                                                                                            
        cancellation_datetime = timezone.make_aware(datetime.combine(date(2025, 1, 1), time(10, 0, 0)))                           
                                                                       
        pickup_datetime_exact_boundary = cancellation_datetime + timedelta(days=7)

        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('500.00'),
            payment_method='online_full',
            pickup_date_offset_days=0,                                                
            refund_policy_snapshot=self.full_payment_policy_snapshot
        )
        booking.pickup_date = pickup_datetime_exact_boundary.date()
        booking.pickup_time = pickup_datetime_exact_boundary.time()
        booking.save()

        result = calculate_hire_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)
        self.assertEqual(result['entitled_amount'], Decimal('500.00'))
        self.assertEqual(result['policy_applied'], "Upfront Payment Policy: Full Refund Policy")
        self.assertEqual(result['days_before_pickup'], 7)

    def test_just_under_boundary_full_refund_days(self):
        """
        Tests cancellation just under the boundary for full refund.
        Should result in a partial refund.
        """
                                                                             
                                                              
                                                                                            
        cancellation_datetime = timezone.make_aware(datetime.combine(date(2025, 1, 1), time(10, 0, 0)))
                                                                                               
        pickup_datetime_just_under = cancellation_datetime + timedelta(days=6, hours=23)                                

        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('500.00'),
            payment_method='online_full',
            pickup_date_offset_days=0,              
            refund_policy_snapshot=self.full_payment_policy_snapshot
        )
        booking.pickup_date = pickup_datetime_just_under.date()
        booking.pickup_time = pickup_datetime_just_under.time()
        booking.save()

        result = calculate_hire_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)
        expected_refund = (Decimal('500.00') * Decimal('50.00')) / Decimal('100.00')
        self.assertEqual(result['entitled_amount'], expected_refund)
        self.assertEqual(result['policy_applied'], "Upfront Payment Policy: Partial Refund Policy (50.00%)")
        self.assertEqual(result['days_before_pickup'], 6)                        

    def test_minimal_refund_zero_percentage(self):
        """
        Tests a scenario where minimal refund percentage is 0%.
        """
        policy_with_zero_minimal = self.full_payment_policy_snapshot.copy()
        policy_with_zero_minimal['cancellation_upfront_minimal_refund_percentage'] = str(Decimal('0.00'))                    

        cancellation_datetime = timezone.now()
                                                                 
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('500.00'),
            payment_method='online_full',
            pickup_date_offset_days=2,                      
            refund_policy_snapshot=policy_with_zero_minimal
        )

        result = calculate_hire_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)
        self.assertEqual(result['entitled_amount'], Decimal('0.00'))
        self.assertEqual(result['policy_applied'], "Upfront Payment Policy: Minimal Refund Policy (0.00%)")
        self.assertEqual(result['days_before_pickup'], 1)

    def test_decimal_precision(self):
        """
        Ensures Decimal objects are handled correctly for precision.
        """
        policy_snapshot = {
            'deposit_enabled': False,
            'cancellation_upfront_full_refund_days': 7,
            'cancellation_upfront_partial_refund_days': 3,
            'cancellation_upfront_partial_refund_percentage': str(Decimal('33.33')),                                       
            'cancellation_upfront_minimal_refund_days': 1,
            'cancellation_upfront_minimal_refund_percentage': str(Decimal('0.00')),
        }

        cancellation_datetime = timezone.now()
                                                                   
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('100.00'),
            payment_method='online_full',
            pickup_date_offset_days=5,                      
            refund_policy_snapshot=policy_snapshot
        )

        result = calculate_hire_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)
                              
        self.assertEqual(result['entitled_amount'], Decimal('33.33'))
        self.assertEqual(result['policy_applied'], "Upfront Payment Policy: Partial Refund Policy (33.33%)")
        self.assertEqual(result['days_before_pickup'], 4)

    def test_total_paid_for_calculation_from_payment_amount(self):
        """
        Ensures total_paid_for_calculation correctly uses booking.payment.amount.
        """
        cancellation_datetime = timezone.now()
                                                                   
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('123.45'),                           
            payment_method='online_full',
            pickup_date_offset_days=9,                      
            refund_policy_snapshot=self.full_payment_policy_snapshot
        )

        result = calculate_hire_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('123.45'))
        self.assertIn("123.45 (100.00% of 123.45).", result['details'])

    def test_total_paid_for_calculation_no_payment_amount(self):
        """
        Ensures total_paid_for_calculation defaults to 0 if payment.amount is missing or None.
        This uses MagicMock to simulate the scenario where payment.amount is None.
        """
        cancellation_datetime = timezone.now()

                                                              
        mock_payment = MagicMock()
        mock_payment.amount = None
        mock_payment.refund_policy_snapshot = self.full_payment_policy_snapshot                         

                                                                
        mock_booking = MagicMock()
        mock_booking.payment = mock_payment                        
        mock_booking.payment_method = 'online_full'
        mock_booking.payment_status = 'paid'
        mock_booking.pickup_date = timezone.now().date() + timedelta(days=9)                           
        mock_booking.pickup_time = time(10, 0)
        mock_booking.get_payment_method_display.return_value = 'Online Full'


        result = calculate_hire_refund_amount(mock_booking, mock_payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('0.00'))
        self.assertIn("0.00 (100.00% of 0.00).", result['details'])                           
        self.assertIn("Cancellation 8 days before pickup.", result['details'])                             
