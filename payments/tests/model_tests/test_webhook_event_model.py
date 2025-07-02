                                                        

from django.test import TestCase
from django.db import IntegrityError
from django.core.exceptions import ValidationError                         
from django.utils import timezone
import datetime
import time                                  

                                                                     
from payments.models import WebhookEvent
                                
from ..test_helpers.model_factories import WebhookEventFactory


class WebhookEventModelTest(TestCase):
    #--

    def setUp(self):
        #--
        WebhookEvent.objects.all().delete()

    def test_create_basic_webhook_event(self):
        #--
        stripe_event_id = "evt_test_12345"
        event_type = "payment_intent.succeeded"

                                                                                           
        event = WebhookEventFactory.create(
            stripe_event_id=stripe_event_id,
            event_type=event_type,
            payload=None                                       
        )

        self.assertIsNotNone(event.pk)
        self.assertEqual(event.stripe_event_id, stripe_event_id)
        self.assertEqual(event.event_type, event_type)
        self.assertIsNotNone(event.received_at)                               
        self.assertIsNone(event.payload)                                     


    def test_stripe_event_id_uniqueness(self):
        #--
        stripe_event_id = "evt_unique_id_1"
        event_type = "charge.succeeded"

        WebhookEventFactory.create(
            stripe_event_id=stripe_event_id,
            event_type=event_type
        )

                                                                       
        with self.assertRaises(IntegrityError):
            WebhookEventFactory.create(
                stripe_event_id=stripe_event_id,
                event_type="charge.failed"                                    
            )

    def test_auto_now_add_for_received_at(self):
        #--
        event = WebhookEventFactory.create(
            stripe_event_id="evt_time_test",
            event_type="invoice.paid"
        )
                                                           
        self.assertIsNotNone(event.received_at)
        time_difference = timezone.now() - event.received_at
        self.assertLess(time_difference, datetime.timedelta(seconds=5))                                  

    def test_payload_json_field(self):
        #--
        payload_data = {
            "id": "pi_xyz",
            "object": "payment_intent",
            "amount": 10000,
            "currency": "aud",
            "status": "succeeded",
            "metadata": {"user_id": "123", "order_id": "abc"}
        }
        event = WebhookEventFactory.create(
            stripe_event_id="evt_with_payload",
            event_type="payment_intent.created",
            payload=payload_data
        )
        self.assertEqual(event.payload, payload_data)

                                                             
        event_empty_payload = WebhookEventFactory.create(
            stripe_event_id="evt_empty_payload",
            event_type="customer.created",
            payload={}                             
        )
        self.assertEqual(event_empty_payload.payload, {})

                               
        event.payload['new_key'] = 'new_value'
        event.save()
        event.refresh_from_db()
        self.assertIn('new_key', event.payload)
        self.assertEqual(event.payload['new_key'], 'new_value')
                                                                           
        expected_updated_payload = {**payload_data, 'new_key': 'new_value'}
        self.assertEqual(event.payload, expected_updated_payload)


    def test_str_method(self):
        #--
        stripe_event_id = "evt_str_method_test"
        event_type = "customer.updated"
                                                        
        event = WebhookEventFactory.create(
            stripe_event_id=stripe_event_id,
            event_type=event_type
        )
                                                                      
                                                                                           
        expected_str = f"Event: {stripe_event_id} ({event_type}) received at {event.received_at}"
        self.assertEqual(str(event), expected_str)


    def test_ordering_by_received_at(self):
        #--
                                                                               
        event1 = WebhookEventFactory.create(stripe_event_id="evt_order_1", event_type="type1")
        time.sleep(0.01)                                  
        event2 = WebhookEventFactory.create(stripe_event_id="evt_order_2", event_type="type2")
        time.sleep(0.01)
        event3 = WebhookEventFactory.create(stripe_event_id="evt_order_3", event_type="type3")

                                                
        all_events = WebhookEvent.objects.all()
        self.assertEqual(list(all_events), [event3, event2, event1])

    def test_max_length_constraints(self):
        #--
        long_id = "a" * 101                         
        long_type = "b" * 101                         

                              
        event_with_long_id = WebhookEvent(                                                      
            stripe_event_id=long_id,
            event_type="short_type"
        )
        with self.assertRaises(ValidationError):                            
            event_with_long_id.full_clean()                                          

                         
        event_with_long_type = WebhookEvent(                                                      
            stripe_event_id="evt_short_id",
            event_type=long_type
        )
        with self.assertRaises(ValidationError):                            
            event_with_long_type.full_clean()                                          

                                              
        valid_id = "a" * 100
        valid_type = "b" * 100
        event = WebhookEventFactory.create(
            stripe_event_id=valid_id,
            event_type=valid_type
        )
        self.assertEqual(event.stripe_event_id, valid_id)
        self.assertEqual(event.event_type, valid_type)
