from decimal import Decimal
from django.test import TestCase
from django.db import IntegrityError
import uuid
import time

from ..test_helpers.model_factories import (
    PaymentFactory,
    MotorcycleFactory,
    MotorcycleConditionFactory,
    TempServiceBookingFactory,
    ServiceBookingFactory,
    ServiceProfileFactory,
)

from payments.models import Payment
from service.models import TempServiceBooking, ServiceBooking, ServiceProfile


class PaymentModelTest(TestCase):
    """
    Unit tests for the Payment model.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods.
        We'll create some related objects that payments can link to.
        """
                                                                
        MotorcycleConditionFactory.create(name='used', display_name='Used')
                               
        cls.motorcycle = MotorcycleFactory.create()
        cls.temp_service_booking = TempServiceBookingFactory.create()
        cls.service_profile = ServiceProfileFactory.create(name="Service Customer Name")
        cls.service_booking = ServiceBookingFactory.create(
            service_profile=cls.service_profile                                      
        )


        cls.stripe_pi_id_1 = "pi_test_12345"
        cls.stripe_pi_id_2 = "pi_test_67890"

    def test_temp_service_booking_relationship(self):
        """
        Test the OneToOneField relationship with TempServiceBooking.
        """
        Payment.objects.all().delete()
        payment = PaymentFactory.create(
            amount=Decimal('100.00'),
            temp_service_booking=self.temp_service_booking
        )
        self.assertEqual(payment.temp_service_booking, self.temp_service_booking)
        self.assertEqual(self.temp_service_booking.payment_for_temp_service, payment)

        with self.assertRaises(IntegrityError):
            PaymentFactory.create(
                amount=Decimal('50.00'),
                temp_service_booking=self.temp_service_booking
            )

    def test_service_booking_relationship(self):
        """
        Test the ForeignKey relationship with ServiceBooking.
        """
        Payment.objects.all().delete()
        payment1 = PaymentFactory.create(
            amount=Decimal('200.00'),
            service_booking=self.service_booking
        )
        payment2 = PaymentFactory.create(
            amount=Decimal('50.00'),
            service_booking=self.service_booking
        )
        self.assertEqual(payment1.service_booking, self.service_booking)
        self.assertEqual(payment2.service_booking, self.service_booking)
        self.assertIn(payment1, self.service_booking.payments_for_service.all())
        self.assertIn(payment2, self.service_booking.payments_for_service.all())
        self.assertEqual(self.service_booking.payments_for_service.count(), 2)

    def test_service_customer_profile_relationship(self):
        """
        Test the ForeignKey relationship with ServiceProfile.
        """
        Payment.objects.all().delete()
        payment1 = PaymentFactory.create(
            amount=Decimal('120.00'),
            service_customer_profile=self.service_profile
        )
        payment2 = PaymentFactory.create(
            amount=Decimal('80.00'),
            service_customer_profile=self.service_profile
        )
        self.assertEqual(payment1.service_customer_profile, self.service_profile)
        self.assertEqual(payment2.service_customer_profile, self.service_profile)
        self.assertIn(payment1, self.service_profile.payments_by_service_customer.all())
        self.assertIn(payment2, self.service_profile.payments_by_service_customer.all())
        self.assertEqual(self.service_profile.payments_by_service_customer.count(), 2)


    def test_stripe_payment_intent_id_uniqueness(self):
        """
        Test that stripe_payment_intent_id is unique.
        """
                                                                          
        Payment.objects.all().delete()
                                                                             
        PaymentFactory.create(
            amount=Decimal('10.00')
        )
        with self.assertRaises(IntegrityError):
                                                                        
                                                           
            duplicate_pi_id = "pi_manual_duplicate_id"
            PaymentFactory.create(amount=Decimal('10.00'), stripe_payment_intent_id=duplicate_pi_id)
            PaymentFactory.create(amount=Decimal('20.00'), stripe_payment_intent_id=duplicate_pi_id)


    def test_default_values(self):
        """
        Test that default values for currency and status are applied.
        """
                                                                          
        Payment.objects.all().delete()
        payment = PaymentFactory.create(amount=Decimal('50.00'))
        self.assertEqual(payment.currency, 'AUD')
                                                                                                   
                                                                                   
                                                                                              

                                                                
        payment_model_default = Payment.objects.create(amount=Decimal('75.00'), stripe_payment_intent_id=f"pi_{uuid.uuid4().hex[:24]}")
        self.assertEqual(payment_model_default.status, 'requires_payment_method')
        self.assertEqual(payment_model_default.currency, 'AUD')


    def test_amount_decimal_field(self):
        """
        Test DecimalField properties for amount.
        """
                                                                          
        Payment.objects.all().delete()
        payment = PaymentFactory.create(amount=Decimal('1234567.89'))
        self.assertEqual(payment.amount, Decimal('1234567.89'))

                                                                  
        payment_rounded = PaymentFactory.create(amount=Decimal('100.123'))
        payment_rounded.refresh_from_db()                                               
        self.assertEqual(payment_rounded.amount, Decimal('100.12'))

                                                     
        large_amount = Decimal('99999999.99')
        payment_large = PaymentFactory.create(amount=large_amount)
        self.assertEqual(payment_large.amount, large_amount)                                                                               
                                                                                                                                          
                                                                                            
    def test_ordering_by_created_at(self):
        """
        Test that payments are ordered by created_at in descending order.
        """
                                                                          
        Payment.objects.all().delete()
                                                                         
                                                                             
        payment1 = PaymentFactory.create(amount=Decimal('10.00'))
        time.sleep(0.01)                                  
        payment2 = PaymentFactory.create(amount=Decimal('20.00'))
        time.sleep(0.01)
        payment3 = PaymentFactory.create(amount=Decimal('30.00'))

                                                  
        all_payments = Payment.objects.all()
        self.assertEqual(list(all_payments), [payment3, payment2, payment1])
                                                                        
        self.assertEqual(Payment.objects.count(), 3)


    def test_metadata_json_field(self):
        """
        Test the metadata JSONField.
        """
                                                                          
        Payment.objects.all().delete()
        metadata_data = {
            "customer_email": "test@example.com",
            "booking_type": "rental",
            "items": ["motorcycle", "helmet"]
        }
        payment = PaymentFactory.create(
            amount=Decimal('300.00'),
            metadata=metadata_data,
        )
        self.assertEqual(payment.metadata, metadata_data)

                                
        payment.metadata['new_key'] = 'new_value'
        payment.save()
        payment.refresh_from_db()
        self.assertEqual(payment.metadata['new_key'], 'new_value')

                                                 
                                                                                                 
        payment_empty_meta = PaymentFactory.create(
            amount=Decimal('50.00'),
            metadata={},
        )
        self.assertEqual(payment_empty_meta.metadata, {})

    def test_stripe_payment_method_id(self):
        """
        Test that stripe_payment_method_id can be set.
        """
                                                                          
        Payment.objects.all().delete()
        payment = PaymentFactory.create(
            amount=Decimal('75.00'),
            stripe_payment_method_id="pm_card_visa",
        )
        self.assertEqual(payment.stripe_payment_method_id, "pm_card_visa")
                                                                                                
        payment_model_default = Payment.objects.create(
            amount=Decimal('75.00'),
            stripe_payment_intent_id=f"pi_{uuid.uuid4().hex[:24]}"
        )
        self.assertIsNone(payment_model_default.description)                     

    def test_description_field(self):
        """
        Test the description TextField.
        """
                                                                          
        Payment.objects.all().delete()
        description_text = "Payment for 3-day motorcycle rental for customer John Doe."
        payment = PaymentFactory.create(
            amount=Decimal('400.00'),
            description=description_text,
        )
        self.assertEqual(payment.description, description_text)

                                     
        payment_blank_desc = PaymentFactory.create(
            amount=Decimal('10.00'),
            description="",
        )
        self.assertEqual(payment_blank_desc.description, "")

                                              
                                                                                                
        payment_null_desc = Payment.objects.create(
            amount=Decimal('20.00'),
            stripe_payment_intent_id=f"pi_{uuid.uuid4().hex[:24]}"
        )
        self.assertIsNone(payment_null_desc.description)