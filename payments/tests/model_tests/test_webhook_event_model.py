# payments/tests/model_tests/test_webhook_event_model.py

from django.test import TestCase
from django.db import IntegrityError
from django.core.exceptions import ValidationError # Import ValidationError
from django.utils import timezone
import datetime
import uuid

from payments.models import WebhookEvent # Import the WebhookEvent model

class WebhookEventModelTest(TestCase):
    """
    Unit tests for the WebhookEvent model.
    """

    def test_create_basic_webhook_event(self):
        """
        Test that a basic WebhookEvent instance can be created with required fields.
        """
        stripe_event_id = "evt_test_12345"
        event_type = "payment_intent.succeeded"

        event = WebhookEvent.objects.create(
            stripe_event_id=stripe_event_id,
            event_type=event_type
        )

        self.assertIsNotNone(event.pk)
        self.assertEqual(event.stripe_event_id, stripe_event_id)
        self.assertEqual(event.event_type, event_type)
        self.assertIsNotNone(event.received_at) # auto_now_add should set this
        self.assertIsNone(event.payload) # Should be None by default

    def test_stripe_event_id_uniqueness(self):
        """
        Test that stripe_event_id is unique.
        """
        stripe_event_id = "evt_unique_id_1"
        event_type = "charge.succeeded"

        WebhookEvent.objects.create(
            stripe_event_id=stripe_event_id,
            event_type=event_type
        )

        # Attempt to create another event with the same stripe_event_id
        with self.assertRaises(IntegrityError):
            WebhookEvent.objects.create(
                stripe_event_id=stripe_event_id,
                event_type="charge.failed" # Different event type, but same ID
            )

    def test_auto_now_add_for_received_at(self):
        """
        Test that 'received_at' is automatically set on creation.
        """
        event = WebhookEvent.objects.create(
            stripe_event_id="evt_time_test",
            event_type="invoice.paid"
        )
        # Check that received_at is set and is close to now
        self.assertIsNotNone(event.received_at)
        time_difference = timezone.now() - event.received_at
        self.assertLess(time_difference, datetime.timedelta(seconds=5)) # Should be created very recently

    def test_payload_json_field(self):
        """
        Test the payload JSONField.
        """
        payload_data = {
            "id": "pi_xyz",
            "object": "payment_intent",
            "amount": 10000,
            "currency": "aud",
            "status": "succeeded",
            "metadata": {"user_id": "123", "order_id": "abc"}
        }
        event = WebhookEvent.objects.create(
            stripe_event_id="evt_with_payload",
            event_type="payment_intent.created",
            payload=payload_data
        )
        self.assertEqual(event.payload, payload_data)

        # Test with an empty payload
        event_empty_payload = WebhookEvent.objects.create(
            stripe_event_id="evt_empty_payload",
            event_type="customer.created",
            payload={}
        )
        self.assertEqual(event_empty_payload.payload, {})

        # Test updating payload
        event.payload['new_key'] = 'new_value'
        event.save()
        event.refresh_from_db()
        self.assertEqual(event.payload['new_key'], 'new_value')
        self.assertEqual(event.payload, {**payload_data, 'new_key': 'new_value'})


    def test_str_method(self):
        """
        Test the __str__ method of WebhookEvent.
        """
        stripe_event_id = "evt_str_method_test"
        event_type = "customer.updated"
        # Create an event to get a received_at timestamp
        event = WebhookEvent.objects.create(
            stripe_event_id=stripe_event_id,
            event_type=event_type
        )
        # Format the received_at timestamp to match the __str__ output
        # Note: timezone.localtime() is good practice if you have TIME_ZONE set in settings
        expected_str = f"Event: {stripe_event_id} ({event_type}) received at {event.received_at}"
        self.assertEqual(str(event), expected_str)


    def test_ordering_by_received_at(self):
        """
        Test that WebhookEvents are ordered by received_at in descending order.
        """
        import time # Needed to ensure distinct creation times

        event1 = WebhookEvent.objects.create(stripe_event_id="evt_order_1", event_type="type1")
        time.sleep(0.01) # Ensure different creation times
        event2 = WebhookEvent.objects.create(stripe_event_id="evt_order_2", event_type="type2")
        time.sleep(0.01)
        event3 = WebhookEvent.objects.create(stripe_event_id="evt_order_3", event_type="type3")

        # Fetch all events and check their order
        all_events = WebhookEvent.objects.all()
        self.assertEqual(list(all_events), [event3, event2, event1])

    def test_max_length_constraints(self):
        """
        Test max_length constraints for char fields.
        """
        long_id = "a" * 101 # Exceeds max_length=100
        long_type = "b" * 101 # Exceeds max_length=100

        # Test stripe_event_id
        event_with_long_id = WebhookEvent(
            stripe_event_id=long_id,
            event_type="short_type"
        )
        with self.assertRaises(ValidationError): # Expecting ValidationError
            event_with_long_id.full_clean() # Call full_clean() to trigger validation

        # Test event_type
        event_with_long_type = WebhookEvent(
            stripe_event_id="evt_short_id",
            event_type=long_type
        )
        with self.assertRaises(ValidationError): # Expecting ValidationError
            event_with_long_type.full_clean() # Call full_clean() to trigger validation

        # Test valid lengths
        valid_id = "a" * 100
        valid_type = "b" * 100
        event = WebhookEvent.objects.create(
            stripe_event_id=valid_id,
            event_type=valid_type
        )
        self.assertEqual(event.stripe_event_id, valid_id)
        self.assertEqual(event.event_type, valid_type)

