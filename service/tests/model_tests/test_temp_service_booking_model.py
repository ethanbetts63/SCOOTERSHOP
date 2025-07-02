from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from datetime import date, time, timedelta
from django.db import models

                                     
from service.models import TempServiceBooking

                      
from ..test_helpers.model_factories import (
    TempServiceBookingFactory,
    ServiceTypeFactory,
    ServiceProfileFactory,
    CustomerMotorcycleFactory
)

class TempServiceBookingModelTest(TestCase):
    

    @classmethod
    def setUpTestData(cls):
        
        cls.service_type = ServiceTypeFactory()
        cls.service_profile = ServiceProfileFactory()
        cls.customer_motorcycle = CustomerMotorcycleFactory(service_profile=cls.service_profile)                                      
        
                                                                  
                                                                                                            
        cls.temp_booking = TempServiceBookingFactory(
            service_type=cls.service_type,
            service_profile=cls.service_profile,
            customer_motorcycle=cls.customer_motorcycle,
            service_date=date.today() + timedelta(days=5),                               
            dropoff_date=date.today() + timedelta(days=3),                               
            dropoff_time=time(10, 0)                               
        )

    def test_temp_service_booking_creation(self):
        
        self.assertIsNotNone(self.temp_booking)
        self.assertIsInstance(self.temp_booking, TempServiceBooking)
                                                               
        self.assertEqual(TempServiceBooking.objects.count(), 1)

    def test_field_attributes(self):
        
        booking = self.temp_booking

                      
        field = booking._meta.get_field('session_uuid')
        self.assertIsInstance(field, models.UUIDField)
        self.assertFalse(field.editable)
        self.assertTrue(field.unique)
        self.assertIsNotNone(field.default)                             

                      
        field = booking._meta.get_field('service_type')
        self.assertIsInstance(field, models.ForeignKey)
        self.assertEqual(field.related_model.__name__, 'ServiceType')
        self.assertEqual(field.remote_field.on_delete, models.PROTECT)
        self.assertFalse(field.null)                 
        self.assertFalse(field.blank)                 

                         
        field = booking._meta.get_field('service_profile')
        self.assertIsInstance(field, models.ForeignKey)
        self.assertEqual(field.related_model.__name__, 'ServiceProfile')
        self.assertEqual(field.remote_field.on_delete, models.CASCADE)
        self.assertTrue(field.null)               
        self.assertTrue(field.blank)                

                             
        field = booking._meta.get_field('customer_motorcycle')
        self.assertIsInstance(field, models.ForeignKey)
        self.assertEqual(field.related_model.__name__, 'CustomerMotorcycle')
        self.assertEqual(field.remote_field.on_delete, models.SET_NULL)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)

                      
        field = booking._meta.get_field('service_date')
        self.assertIsInstance(field, models.DateField)
        self.assertFalse(field.null)                 
        self.assertFalse(field.blank)                 

                      
        field = booking._meta.get_field('dropoff_date')
        self.assertIsInstance(field, models.DateField)
        self.assertTrue(field.null)               
        self.assertTrue(field.blank)                

                      
        field = booking._meta.get_field('dropoff_time')
        self.assertIsInstance(field, models.TimeField)
        self.assertTrue(field.null)               
        self.assertTrue(field.blank)                

                               
        field = booking._meta.get_field('estimated_pickup_date')
        self.assertIsInstance(field, models.DateField)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)

                        
        field = booking._meta.get_field('customer_notes')
        self.assertIsInstance(field, models.TextField)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)

                                   
        field = booking._meta.get_field('calculated_deposit_amount')
        self.assertIsInstance(field, models.DecimalField)
        self.assertEqual(field.max_digits, 10)
        self.assertEqual(field.decimal_places, 2)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)

                                
        field = booking._meta.get_field('created_at')
        self.assertIsInstance(field, models.DateTimeField)
        self.assertTrue(field.auto_now_add)
        field = booking._meta.get_field('updated_at')
        self.assertIsInstance(field, models.DateTimeField)
        self.assertTrue(field.auto_now)

    def test_required_fields_validation(self):
        
                                   
        with self.assertRaises(ValidationError) as cm:
            TempServiceBookingFactory.build(
                service_type=None,
                service_profile=self.service_profile,                               
                service_date=date.today(),
                dropoff_date=date.today(),
                dropoff_time=time(9,0)
            ).full_clean()
        self.assertIn('service_type', cm.exception.message_dict)

                                   
        with self.assertRaises(ValidationError) as cm:
            TempServiceBookingFactory.build(
                service_type=self.service_type,
                service_profile=self.service_profile,                               
                service_date=None,                                     
                dropoff_date=date.today(),                                  
                dropoff_time=time(9,0)
            ).full_clean()
        self.assertIn('service_date', cm.exception.message_dict)

                                                                                               
        try:
            TempServiceBookingFactory.build(
                service_type=self.service_type,                 
                service_profile=None,               
                service_date=date.today(),                 
                dropoff_date=date.today(),               
                dropoff_time=time(9,0)               
            ).full_clean()
        except ValidationError:
            self.fail("ValidationError raised unexpectedly for nullable service_profile.")

                                                                                            
        try:
            TempServiceBookingFactory.build(
                service_type=self.service_type,                 
                service_profile=self.service_profile,
                service_date=date.today(),                 
                dropoff_date=None,               
                dropoff_time=time(9,0)               
            ).full_clean()
        except ValidationError:
            self.fail("ValidationError raised unexpectedly for nullable dropoff_date.")

                                                                                            
        try:
            TempServiceBookingFactory.build(
                service_type=self.service_type,                 
                service_profile=self.service_profile,
                service_date=date.today(),                 
                dropoff_date=date.today(),               
                dropoff_time=None               
            ).full_clean()
        except ValidationError:
            self.fail("ValidationError raised unexpectedly for nullable dropoff_time.")


                                                                                             
        try:
            TempServiceBookingFactory.build(
                service_type=self.service_type,
                service_profile=None,                                    
                service_date=date.today(),
                dropoff_date=None,                                 
                dropoff_time=None                                 
            ).full_clean()
        except ValidationError as e:
            self.fail(f"full_clean raised ValidationError unexpectedly: {e.message_dict}")

    def test_session_uuid_uniqueness(self):
        
                                               
        first_booking = TempServiceBookingFactory(
            service_type=self.service_type,
            service_profile=self.service_profile                                  
        )
        
                                                              
        with self.assertRaises(IntegrityError):
                                                                                 
            TempServiceBookingFactory.create(
                session_uuid=first_booking.session_uuid,
                service_type=self.service_type,
                service_profile=self.service_profile                                  
            )

    def test_payment_method_choices(self):
        
                                  
        try:
            TempServiceBookingFactory.build(
                service_type=self.service_type,
                service_profile=self.service_profile,
                payment_method='online_full'
            ).full_clean()
        except ValidationError as e:
            self.fail(f"full_clean raised ValidationError unexpectedly for valid payment_method: {e.message_dict}")

                                     
        with self.assertRaises(ValidationError) as cm:
            TempServiceBookingFactory.build(
                service_type=self.service_type,
                service_profile=self.service_profile,
                payment_method='invalid_option'
            ).full_clean()
        self.assertIn('payment_method', cm.exception.message_dict)
        self.assertIn("Value 'invalid_option' is not a valid choice.", str(cm.exception))

                                  
        try:
            TempServiceBookingFactory.build(
                service_type=self.service_type,
                service_profile=self.service_profile,
                payment_method=None
            ).full_clean()
        except ValidationError as e:
            self.fail(f"full_clean raised ValidationError unexpectedly for None payment_method: {e.message_dict}")

    def test_dropoff_date_not_in_past(self):
        
                                                                                                                  
        past_date = date.today() - timedelta(days=1)
        try:
            TempServiceBookingFactory.build(
                service_type=self.service_type,
                service_profile=self.service_profile,
                service_date=date.today(),                                   
                dropoff_date=past_date
            ).full_clean()
        except ValidationError:
            self.fail("ValidationError raised for past dropoff_date, but model doesn't enforce this.")

                                              
        try:
            TempServiceBookingFactory.build(
                service_type=self.service_type,
                service_profile=self.service_profile,
                service_date=date.today(),                                   
                dropoff_date=date.today()
            ).full_clean()
        except ValidationError as e:
            self.fail(f"full_clean raised ValidationError unexpectedly for current dropoff_date: {e.message_dict}")

                                             
        future_date = date.today() + timedelta(days=7)
        try:
            TempServiceBookingFactory.build(
                service_type=self.service_type,
                service_profile=self.service_profile,
                service_date=date.today(),                                   
                dropoff_date=future_date
            ).full_clean()
        except ValidationError as e:
            self.fail(f"full_clean raised ValidationError unexpectedly for future dropoff_date: {e.message_dict}")

    def test_calculated_deposit_amount_validation(self):
        
                                                                                                            
        negative_amount = -10.50
        try:
            TempServiceBookingFactory.build(
                service_type=self.service_type,
                service_profile=self.service_profile,
                calculated_deposit_amount=negative_amount
            ).full_clean()
        except ValidationError:
            self.fail("ValidationError raised for negative calculated_deposit_amount, but model doesn't enforce this.")

                                      
        try:
            TempServiceBookingFactory.build(
                service_type=self.service_type,
                service_profile=self.service_profile,
                calculated_deposit_amount=0.00
            ).full_clean()
        except ValidationError as e:
            self.fail(f"full_clean raised ValidationError unexpectedly for zero calculated_deposit_amount: {e.message_dict}")

                                                 
        try:
            TempServiceBookingFactory.build(
                service_type=self.service_type,
                service_profile=self.service_profile,
                calculated_deposit_amount=50.00
            ).full_clean()
        except ValidationError as e:
            self.fail(f"full_clean raised ValidationError unexpectedly for positive calculated_deposit_amount: {e.message_dict}")

                                  
        try:
            TempServiceBookingFactory.build(
                service_type=self.service_type,
                service_profile=self.service_profile,
                calculated_deposit_amount=None
            ).full_clean()
        except ValidationError as e:
            self.fail(f"full_clean raised ValidationError unexpectedly for None calculated_deposit_amount: {e.message_dict}")


    def test_timestamps_auto_now_add_and_auto_now(self):
        
        booking = TempServiceBookingFactory(
            service_type=self.service_type,
            service_profile=self.service_profile
        )
        initial_created_at = booking.created_at
        initial_updated_at = booking.updated_at

                                              
        self.assertIsNotNone(initial_created_at)
        self.assertIsNotNone(initial_updated_at)
        self.assertLessEqual(initial_created_at, initial_updated_at)

                                     
        import time
        time.sleep(0.01)                                                           
        booking.customer_notes = "Updated notes"
        booking.save()

                                                             
        self.assertGreater(booking.updated_at, initial_updated_at)
                                           
        self.assertEqual(booking.created_at, initial_created_at)

    def test_foreign_key_on_delete_service_type(self):
        
                                                                         
        service_type_to_delete = ServiceTypeFactory()
        booking_to_test = TempServiceBookingFactory(
            service_type=service_type_to_delete,
            service_profile=self.service_profile                               
        )
        
        with self.assertRaises(models.ProtectedError):
            service_type_to_delete.delete()
        
                                         
        self.assertTrue(TempServiceBooking.objects.filter(pk=booking_to_test.pk).exists())

    def test_foreign_key_on_delete_service_profile(self):
        
                                                                
        service_profile_to_delete = ServiceProfileFactory()
        booking_to_test = TempServiceBookingFactory(
            service_profile=service_profile_to_delete,
            service_type=self.service_type                            
        )
        
                                    
        service_profile_to_delete.delete()
        
                                            
        self.assertFalse(TempServiceBooking.objects.filter(pk=booking_to_test.pk).exists())

    def test_foreign_key_on_delete_customer_motorcycle(self):
        
                                                                    
        customer_motorcycle_to_delete = CustomerMotorcycleFactory(service_profile=self.service_profile)
        booking_with_motorcycle = TempServiceBookingFactory(
            customer_motorcycle=customer_motorcycle_to_delete,
            service_type=self.service_type,
            service_profile=self.service_profile
        )
        
                                        
        customer_motorcycle_to_delete.delete()
        
                                                        
        booking_with_motorcycle.refresh_from_db()
        
                                                   
        self.assertIsNone(booking_with_motorcycle.customer_motorcycle)
                                                
        self.assertTrue(TempServiceBooking.objects.filter(pk=booking_with_motorcycle.pk).exists())
