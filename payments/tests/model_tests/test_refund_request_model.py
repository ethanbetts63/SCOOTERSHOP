                                             

from decimal import Decimal
from django.test import TestCase
from django.db import IntegrityError
import uuid
from django.utils import timezone
import datetime                                
import time                        

                        
from payments.tests.test_helpers.model_factories import (
    RefundRequestFactory,
    HireBookingFactory,
    ServiceBookingFactory,
    PaymentFactory,
    DriverProfileFactory,
    ServiceProfileFactory,
    UserFactory,
    MotorcycleConditionFactory,                               
    MotorcycleFactory,                      
    ServiceTypeFactory,                                   
    CustomerMotorcycleFactory,                                   
)

                                           
from payments.models import RefundRequest, Payment
from hire.models import HireBooking, DriverProfile
from service.models import ServiceBooking, ServiceProfile
from django.contrib.auth import get_user_model

User = get_user_model()


class RefundRequestModelTest(TestCase):
    """
    Unit tests for the RefundRequest model.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods.
        We'll create some related objects that RefundRequest can link to.
        """
                                                                
        MotorcycleConditionFactory.create(name='hire', display_name='Hire')

        cls.motorcycle = MotorcycleFactory.create()
        cls.driver_profile = DriverProfileFactory.create(name="Hire Driver")
        cls.service_profile = ServiceProfileFactory.create(name="Service Customer")
        cls.user = UserFactory.create(username='teststaff', is_staff=True)                         

        cls.hire_booking = HireBookingFactory.create(
            motorcycle=cls.motorcycle,
            driver_profile=cls.driver_profile,
            total_hire_price=Decimal('500.00'),
            grand_total=Decimal('550.00'),
            amount_paid=Decimal('550.00')
        )

        cls.service_type = ServiceTypeFactory.create()
        cls.customer_motorcycle = CustomerMotorcycleFactory.create(service_profile=cls.service_profile)

        cls.service_booking = ServiceBookingFactory.create(
            service_profile=cls.service_profile,
            service_type=cls.service_type,
            customer_motorcycle=cls.customer_motorcycle,
            calculated_total=Decimal('300.00'),
            amount_paid=Decimal('300.00')
        )

        cls.payment_for_hire = PaymentFactory.create(
            amount=Decimal('550.00'),
            hire_booking=cls.hire_booking,
            status='succeeded'
        )

        cls.payment_for_service = PaymentFactory.create(
            amount=Decimal('300.00'),
            service_booking=cls.service_booking,
            status='succeeded'
        )

    def test_create_basic_refund_request(self):
        """
        Test that a basic RefundRequest instance can be created with required fields.
        """
                                                                   
        RefundRequest.objects.all().delete()

        refund_request = RefundRequestFactory.create(
            hire_booking=self.hire_booking,
            payment=self.payment_for_hire,
            driver_profile=self.driver_profile,
            reason="Customer cancelled booking due to unforeseen circumstances.",
            amount_to_refund=Decimal('250.00'),
            status='pending',
            request_email="customer@example.com",
            is_admin_initiated=False                                                               
        )

        self.assertIsNotNone(refund_request.pk)
        self.assertEqual(refund_request.hire_booking, self.hire_booking)
        self.assertEqual(refund_request.payment, self.payment_for_hire)
        self.assertEqual(refund_request.driver_profile, self.driver_profile)
        self.assertEqual(refund_request.reason, "Customer cancelled booking due to unforeseen circumstances.")
        self.assertEqual(refund_request.amount_to_refund, Decimal('250.00'))
        self.assertEqual(refund_request.status, 'pending')
        self.assertEqual(refund_request.request_email, "customer@example.com")
        self.assertIsNotNone(refund_request.requested_at)
        self.assertIsNone(refund_request.processed_by)
        self.assertIsNone(refund_request.processed_at)
        self.assertFalse(refund_request.is_admin_initiated)
        self.assertIsNotNone(refund_request.verification_token)
        self.assertIsNotNone(refund_request.token_created_at)

    def test_str_method_hire_booking(self):
        """
        Test the __str__ method when a hire_booking is linked.
        """
        refund_request = RefundRequestFactory.create(
            hire_booking=self.hire_booking,
            service_booking=None,                                                     
            status='approved'
        )
        expected_str = f"Refund Request for Booking {self.hire_booking.booking_reference} - Status: {refund_request.status}"
        self.assertEqual(str(refund_request), expected_str)

    def test_str_method_service_booking(self):
        """
        Test the __str__ method when a service_booking is linked.
        """
        refund_request = RefundRequestFactory.create(
            hire_booking=None,                                                                        
            service_booking=self.service_booking,
            status='rejected'
        )
        expected_str = f"Refund Request for Booking {self.service_booking.service_booking_reference} - Status: {refund_request.status}"
        self.assertEqual(str(refund_request), expected_str)

    def test_str_method_no_booking(self):
        """
        Test the __str__ method when no booking is linked.
        """
        refund_request = RefundRequestFactory.create(
            hire_booking=None,
            service_booking=None,
            status='pending'
        )
        expected_str = f"Refund Request for N/A - Status: {refund_request.status}"
        self.assertEqual(str(refund_request), expected_str)

    def test_save_method_verification_token_generation(self):
        """
        Test that verification_token is generated automatically on save if not set.
        """
                                                                                     
        refund_request = RefundRequestFactory.build(
            hire_booking=self.hire_booking,
            payment=self.payment_for_hire,
            driver_profile=self.driver_profile,
            service_profile=self.service_profile,                                                          
            verification_token=None                                               
        )
        self.assertIsNone(refund_request.verification_token)
        refund_request.save()                                          
        self.assertIsNotNone(refund_request.verification_token)
        self.assertIsInstance(refund_request.verification_token, uuid.UUID)

                                                              
        original_token = refund_request.verification_token
        refund_request.reason = "Updated reason."
        refund_request.save()
        refund_request.refresh_from_db()                                                  
        self.assertEqual(refund_request.verification_token, original_token)

    def test_relationships(self):
        """
        Test all ForeignKey relationships.
        """
        refund_request = RefundRequestFactory.create(
            hire_booking=self.hire_booking,
            service_booking=self.service_booking,                                            
            payment=self.payment_for_hire,
            driver_profile=self.driver_profile,
            service_profile=self.service_profile,
            processed_by=self.user
        )

        self.assertEqual(refund_request.hire_booking, self.hire_booking)
        self.assertEqual(refund_request.service_booking, self.service_booking)
        self.assertEqual(refund_request.payment, self.payment_for_hire)
        self.assertEqual(refund_request.driver_profile, self.driver_profile)
        self.assertEqual(refund_request.service_profile, self.service_profile)
        self.assertEqual(refund_request.processed_by, self.user)

                                                      
        self.assertIn(refund_request, self.hire_booking.refund_requests.all())
        self.assertIn(refund_request, self.service_booking.refund_requests.all())
        self.assertIn(refund_request, self.payment_for_hire.refund_requests.all())
        self.assertIn(refund_request, self.driver_profile.refund_requests_related_driver.all())
        self.assertIn(refund_request, self.service_profile.refund_requests_related_service_profile.all())
        self.assertIn(refund_request, self.user.processed_refund_requests.all())

    def test_on_delete_hire_booking_set_null(self):
        """
        Test that hire_booking is set to NULL when HireBooking is deleted.
        """
        refund_request = RefundRequestFactory.create(hire_booking=self.hire_booking)
        hire_booking_id = self.hire_booking.id
        self.hire_booking.delete()
                                                                             
        refund_request.refresh_from_db()
        self.assertIsNone(refund_request.hire_booking)
        self.assertFalse(HireBooking.objects.filter(id=hire_booking_id).exists())
        self.assertTrue(RefundRequest.objects.filter(id=refund_request.id).exists())                             

    def test_on_delete_service_booking_set_null(self):
        """
        Test that service_booking is set to NULL when ServiceBooking is deleted.
        """
        refund_request = RefundRequestFactory.create(
            hire_booking=None,                                                               
            service_booking=self.service_booking
        )
        service_booking_id = self.service_booking.id
        self.service_booking.delete()
                                                                             
        refund_request.refresh_from_db()
        self.assertIsNone(refund_request.service_booking)
        self.assertFalse(ServiceBooking.objects.filter(id=service_booking_id).exists())
        self.assertTrue(RefundRequest.objects.filter(id=refund_request.id).exists())

    def test_on_delete_payment_set_null(self):
        """
        Test that payment is set to NULL when Payment is deleted.
        """
        refund_request = RefundRequestFactory.create(payment=self.payment_for_hire)
        payment_id = self.payment_for_hire.id
        self.payment_for_hire.delete()
        refund_request.refresh_from_db()
        self.assertIsNone(refund_request.payment)
        self.assertFalse(Payment.objects.filter(id=payment_id).exists())
        self.assertTrue(RefundRequest.objects.filter(id=refund_request.id).exists())

    def test_on_delete_driver_profile_set_null(self):
        """
        Test that driver_profile is set to NULL when DriverProfile is deleted.
        """
        refund_request = RefundRequestFactory.create(driver_profile=self.driver_profile)
        driver_profile_id = self.driver_profile.id
        self.driver_profile.delete()
        refund_request.refresh_from_db()
        self.assertIsNone(refund_request.driver_profile)
        self.assertFalse(DriverProfile.objects.filter(id=driver_profile_id).exists())
        self.assertTrue(RefundRequest.objects.filter(id=refund_request.id).exists())

    def test_on_delete_service_profile_set_null(self):
        """
        Test that service_profile is set to NULL when ServiceProfile is deleted.
        """
        refund_request = RefundRequestFactory.create(service_profile=self.service_profile)
        service_profile_id = self.service_profile.id
        self.service_profile.delete()
        refund_request.refresh_from_db()
        self.assertIsNone(refund_request.service_profile)
        self.assertFalse(ServiceProfile.objects.filter(id=service_profile_id).exists())
        self.assertTrue(RefundRequest.objects.filter(id=refund_request.id).exists())

    def test_on_delete_processed_by_set_null(self):
        """
        Test that processed_by is set to NULL when the User is deleted.
        """
        refund_request = RefundRequestFactory.create(processed_by=self.user)
        user_id = self.user.id
        self.user.delete()
        refund_request.refresh_from_db()
        self.assertIsNone(refund_request.processed_by)
        self.assertFalse(User.objects.filter(id=user_id).exists())
        self.assertTrue(RefundRequest.objects.filter(id=refund_request.id).exists())

    def test_status_choices_and_default(self):
        """
        Test that the status field correctly uses choices and has a default value.
        """
                                                                                            
        refund_request_default = RefundRequest.objects.create(
            hire_booking=self.hire_booking,
            payment=self.payment_for_hire,
            amount_to_refund=Decimal('10.00'),
            request_email="default@example.com",
                                                                                             
            driver_profile=self.driver_profile
        )
        self.assertEqual(refund_request_default.status, 'unverified')

                                                             
        refund_request = RefundRequestFactory.create(
            hire_booking=self.hire_booking,
            payment=self.payment_for_hire,
            driver_profile=self.driver_profile,
            amount_to_refund=Decimal('50.00'),
            request_email="valid@example.com"
        )
        for choice_value, _ in RefundRequest.STATUS_CHOICES:
            refund_request.status = choice_value
            refund_request.full_clean()                           
            refund_request.save()
            refund_request.refresh_from_db()
            self.assertEqual(refund_request.status, choice_value)

                                                                                    
        refund_request_invalid = RefundRequestFactory.create(
            hire_booking=self.hire_booking,
            payment=self.payment_for_hire,
            driver_profile=self.driver_profile,
            amount_to_refund=Decimal('10.00'),
            request_email="invalid@example.com"
        )
        refund_request_invalid.status = 'invalid_status'
        with self.assertRaises(Exception):                                                                         
            refund_request_invalid.full_clean()

    def test_amount_to_refund_decimal_field(self):
        """
        Test DecimalField properties for amount_to_refund.
        """
        amount = Decimal('12345.67')
        refund_request = RefundRequestFactory.create(amount_to_refund=amount)
        self.assertEqual(refund_request.amount_to_refund, amount)

                                                                  
        amount_rounded = Decimal('100.123')
        refund_request_rounded = RefundRequestFactory.create(amount_to_refund=amount_rounded)
        refund_request_rounded.refresh_from_db()
        self.assertEqual(refund_request_rounded.amount_to_refund, Decimal('100.12'))

                             
        refund_request_null = RefundRequestFactory.create(amount_to_refund=None)
        self.assertIsNone(refund_request_null.amount_to_refund)

    def test_reason_and_rejection_reason_fields(self):
        """
        Test TextField properties for reason and rejection_reason.
        """
        reason_text = "The customer changed their mind about the booking."
        rejection_text = "Refund denied as per 24-hour cancellation policy."
        refund_request = RefundRequestFactory.create(
            reason=reason_text,
            rejection_reason=rejection_text
        )
        self.assertEqual(refund_request.reason, reason_text)
        self.assertEqual(refund_request.rejection_reason, rejection_text)

                           
        refund_request_blank_reason = RefundRequestFactory.create(reason="")
        self.assertEqual(refund_request_blank_reason.reason, "")

                                    
        refund_request_null_rejection = RefundRequestFactory.create(rejection_reason=None)
        self.assertIsNone(refund_request_null_rejection.rejection_reason)

    def test_timestamps(self):
        """
        Test requested_at (auto_now_add) and processed_at (nullable DateTimeField).
        """
                                                       
        refund_request = RefundRequestFactory.create(processed_at=None)
        self.assertIsNotNone(refund_request.requested_at)
        self.assertIsNone(refund_request.processed_at)

                                   
        processed_time = timezone.now() - datetime.timedelta(hours=1)
        refund_request.processed_at = processed_time
        refund_request.save()
        refund_request.refresh_from_db()
                                                                                 
        self.assertAlmostEqual(refund_request.processed_at, processed_time, delta=datetime.timedelta(seconds=1))

    def test_is_admin_initiated_field(self):
        """
        Test the is_admin_initiated BooleanField.
        """
        refund_request_admin = RefundRequestFactory.create(is_admin_initiated=True)
        self.assertTrue(refund_request_admin.is_admin_initiated)

        refund_request_customer = RefundRequestFactory.create(is_admin_initiated=False)
        self.assertFalse(refund_request_customer.is_admin_initiated)

                                    
        refund_request_default = RefundRequest.objects.create(
            hire_booking=self.hire_booking,
            payment=self.payment_for_hire,
            amount_to_refund=Decimal('10.00'),
            request_email="default@example.com",
            driver_profile=self.driver_profile                              
        )
        self.assertFalse(refund_request_default.is_admin_initiated)

    def test_refund_calculation_details_json_field(self):
        """
        Test the refund_calculation_details JSONField.
        """
        details_data = {
            "policy_version": "2.0",
            "original_amount": "500.00",
            "deductions": {"stripe_fee": "15.00"},
            "calculated_refund": "485.00"
        }
        refund_request = RefundRequestFactory.create(refund_calculation_details=details_data)
        self.assertEqual(refund_request.refund_calculation_details, details_data)

                                 
        refund_request.refund_calculation_details['notes'] = 'Additional calculation details.'
        refund_request.save()
        refund_request.refresh_from_db()
        self.assertEqual(refund_request.refund_calculation_details['notes'], 'Additional calculation details.')

                                                                     
                                                                                               
                                                                                       
        refund_request_default_json = RefundRequest.objects.create(
            hire_booking=self.hire_booking,
            payment=self.payment_for_hire,
            driver_profile=self.driver_profile,
            amount_to_refund=Decimal('1.00'),
            request_email="default_json@example.com",
                                                                                                     
        )
        self.assertEqual(refund_request_default_json.refund_calculation_details, {})

    def test_request_email_field(self):
        """
        Test the request_email EmailField.
        """
        email = "user.refund@example.com"
        refund_request = RefundRequestFactory.create(request_email=email)
        self.assertEqual(refund_request.request_email, email)

                         
        refund_request_null_email = RefundRequestFactory.create(request_email=None)
        self.assertIsNone(refund_request_null_email.request_email)

                          
        refund_request_blank_email = RefundRequestFactory.create(request_email="")
        self.assertEqual(refund_request_blank_email.request_email, "")

                                                  
        refund_request_invalid_email = RefundRequestFactory.build(request_email="invalid-email")
                                                                                  
        refund_request_invalid_email.hire_booking = self.hire_booking
        refund_request_invalid_email.payment = self.payment_for_hire
        refund_request_invalid_email.driver_profile = self.driver_profile
        refund_request_invalid_email.amount_to_refund = Decimal('1.00')
        with self.assertRaises(Exception):                                                                         
            refund_request_invalid_email.full_clean()

    def test_verification_token_and_token_created_at(self):
        """
        Test the verification_token (UUIDField) and token_created_at (DateTimeField).
        """
                                                    
        explicit_token = uuid.uuid4()
        explicit_time = timezone.now() - datetime.timedelta(days=1)
        refund_request = RefundRequestFactory.create(
            verification_token=explicit_token,
            token_created_at=explicit_time
        )
        self.assertEqual(refund_request.verification_token, explicit_token)
        self.assertAlmostEqual(refund_request.token_created_at, explicit_time, delta=datetime.timedelta(seconds=1))

                                               
        refund_request_default_token = RefundRequest.objects.create(
            hire_booking=self.hire_booking,
            payment=self.payment_for_hire,
            driver_profile=self.driver_profile,                              
            amount_to_refund=Decimal('10.00'),
            request_email="default2@example.com"
        )
        self.assertIsNotNone(refund_request_default_token.verification_token)
        self.assertIsInstance(refund_request_default_token.verification_token, uuid.UUID)
        self.assertIsNotNone(refund_request_default_token.token_created_at)
                                                     
        self.assertAlmostEqual(refund_request_default_token.token_created_at, timezone.now(), delta=datetime.timedelta(seconds=1))

    def test_staff_notes_field(self):
        """
        Test the staff_notes TextField.
        """
        notes = "Followed up with customer; refund processed on 2023-01-15."
        refund_request = RefundRequestFactory.create(staff_notes=notes)
        self.assertEqual(refund_request.staff_notes, notes)

                                
        refund_request_blank = RefundRequestFactory.create(staff_notes="")
        self.assertEqual(refund_request_blank.staff_notes, "")

    def test_stripe_refund_id_field(self):
        """
        Test the stripe_refund_id CharField.
        """
        stripe_id = "re_123abcDEFgHIJKLmnopqrsTUV"
        refund_request = RefundRequestFactory.create(stripe_refund_id=stripe_id)
        self.assertEqual(refund_request.stripe_refund_id, stripe_id)

                             
        refund_request_null_id = RefundRequestFactory.create(stripe_refund_id=None)
        self.assertIsNone(refund_request_null_id.stripe_refund_id)

        refund_request_blank_id = RefundRequestFactory.create(stripe_refund_id="")
        self.assertEqual(refund_request_blank_id.stripe_refund_id, "")
