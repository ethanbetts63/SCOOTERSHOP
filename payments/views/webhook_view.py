# payments/views/webhook_view.py
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.db import transaction
from django.utils import timezone
import stripe
import json
import logging

from payments.models import Payment, WebhookEvent 
from payments.webhook_handlers import WEBHOOK_HANDLERS 

logger = logging.getLogger(__name__)

@csrf_exempt
def stripe_webhook(request):
    """
    Stripe webhook endpoint for receiving and processing payment events.
    This view is generic and dispatches specific business logic to handlers
    based on metadata in the PaymentIntent.
    """
    print("DEBUG: Entering stripe_webhook view.") # Debug print
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    event = None

    logger.info("Received Stripe webhook request.")
    print(f"DEBUG: Webhook Payload: {payload.decode('utf-8')[:200]}...") # Print first 200 chars of payload
    print(f"DEBUG: Signature Header: {sig_header}") # Debug print

    # 1. Verify Stripe Signature
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
        logger.info(f"Stripe webhook signature verified successfully for event ID: {event['id']}")
        print(f"DEBUG: Webhook signature verified. Event ID: {event['id']}, Type: {event['type']}") # Debug print
    except ValueError as e:
        # Invalid payload
        logger.error(f"Webhook Error: Invalid payload: {e}")
        print(f"DEBUG: Webhook Error: Invalid payload: {e}") # Debug print
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        logger.error(f"Webhook Error: Invalid signature: {e}")
        print(f"DEBUG: Webhook Error: Invalid signature: {e}") # Debug print
        return HttpResponse(status=400)
    except Exception as e:
        logger.error(f"Webhook Error: Unexpected error during event construction: {e}", exc_info=True)
        print(f"DEBUG: Webhook Error: Unexpected error during event construction: {e}") # Debug print
        return HttpResponse(status=500)

    # 2. Idempotency Check: Record the event and check if already processed
    # This prevents duplicate processing if Stripe retries sending the event.
    try:
        with transaction.atomic():
            # Try to create a new WebhookEvent record.
            # If stripe_event_id is unique, it will succeed.
            # If it already exists, IntegrityError will be raised.
            WebhookEvent.objects.create(
                stripe_event_id=event['id'],
                event_type=event['type'],
                payload=event.to_dict(), # Store full payload for debugging
                received_at=timezone.now()
            )
            logger.info(f"Successfully recorded new webhook event: {event['id']} ({event['type']})")
            print(f"DEBUG: Webhook event {event['id']} ({event['type']}) recorded.") # Debug print
    except Exception as e:
        # This typically means the event ID already exists (IntegrityError)
        # or another database error occurred during recording.
        # If it's an IntegrityError, we've already processed this event.
        # If it's another error, we should log it and potentially return 500.
        logger.warning(f"Webhook event {event['id']} ({event['type']}) already processed or failed to record: {e}")
        print(f"DEBUG: Webhook event {event['id']} already processed or failed to record: {e}") # Debug print
        return HttpResponse(status=200) # Acknowledge receipt even if already processed

    # 3. Process the event based on its type
    event_type = event['type']
    event_data = event['data']['object'] # This is the PaymentIntent object for PI events
    payment_intent_id = event_data.get('id')

    logger.info(f"Processing Stripe webhook event: {event_type} for PaymentIntent {payment_intent_id}")
    print(f"DEBUG: Processing event type: {event_type} for PI ID: {payment_intent_id}") # Debug print

    # Handle PaymentIntent-related events
    if event_type.startswith('payment_intent.'):
        print(f"DEBUG: Event is payment_intent related: {event_type}") # Debug print
        try:
            with transaction.atomic():
                # Retrieve the Payment object from your database.
                # Use select_for_update to lock the row during this transaction
                # to prevent race conditions if multiple webhooks for the same PI arrive.
                payment_obj = Payment.objects.select_for_update().get(stripe_payment_intent_id=payment_intent_id)
                logger.debug(f"Found Payment DB object {payment_obj.id} for PaymentIntent {payment_intent_id}")
                print(f"DEBUG: Found Payment DB object {payment_obj.id} for PI: {payment_intent_id}") # Debug print

                # Update the Payment object's status in your database
                # Only update if the status has actually changed to avoid unnecessary DB writes
                if payment_obj.status != event_data['status']:
                    payment_obj.status = event_data['status']
                    # Update amount and currency from Stripe's source of truth if needed
                    payment_obj.amount = event_data['amount'] / 100
                    payment_obj.currency = event_data['currency'].upper()
                    payment_obj.save()
                    logger.info(f"Updated Payment DB object {payment_obj.id} status to '{payment_obj.status}'.")
                    print(f"DEBUG: Updated Payment DB object {payment_obj.id} status to '{payment_obj.status}'.") # Debug print
                else:
                    logger.info(f"Payment DB object {payment_obj.id} status already '{payment_obj.status}'. No update needed.")
                    print(f"DEBUG: Payment DB object {payment_obj.id} status already '{payment_obj.status}'.") # Debug print

                # 4. Dispatch to specific business logic handler
                # Get the booking_type from the PaymentIntent's metadata
                booking_type = event_data.get('metadata', {}).get('booking_type')
                print(f"DEBUG: Booking type from metadata: {booking_type}") # Debug print

                if booking_type and booking_type in WEBHOOK_HANDLERS:
                    # Check if there's a specific handler for this event type and booking type
                    handler = WEBHOOK_HANDLERS[booking_type].get(event_type)
                    if handler:
                        logger.info(f"Dispatching to handler: {handler.__name__} for booking_type '{booking_type}' and event '{event_type}'")
                        print(f"DEBUG: Dispatching to handler: {handler.__name__}") # Debug print
                        handler(payment_obj, event_data)
                        print(f"DEBUG: Handler {handler.__name__} executed.") # Debug print
                    else:
                        logger.info(f"No specific handler found for booking_type '{booking_type}' and event type '{event_type}'.")
                        print(f"DEBUG: No specific handler for {booking_type} and {event_type}.") # Debug print
                else:
                    logger.warning(f"No 'booking_type' found in PaymentIntent metadata or handler not registered for PaymentIntent {payment_intent_id}.")
                    print(f"DEBUG: No booking_type in metadata or handler not registered for PI {payment_intent_id}.") # Debug print

        except Payment.DoesNotExist:
            logger.warning(f"Payment object not found for Stripe Intent ID: {payment_intent_id}. This might indicate a missing DB record for a Stripe event.")
            print(f"DEBUG: WARNING - Payment object not found for PI ID: {payment_intent_id}.") # Debug print
        except Exception as e:
            logger.exception(f"Error processing {event_type} for PaymentIntent {payment_intent_id}: {e}")
            print(f"DEBUG: ERROR - Exception processing {event_type} for PI {payment_intent_id}: {e}") # Debug print
            # Return 500 to Stripe to retry sending the webhook
            return HttpResponse(status=500)
    else:
        # Handle other Stripe events if necessary (e.g., charge.refunded, customer.created)
        logger.info(f"Unhandled Stripe event type: {event_type}")
        print(f"DEBUG: Unhandled Stripe event type: {event_type}") # Debug print

    # Always return a 200 OK to Stripe to acknowledge receipt
    print("DEBUG: Webhook processing complete. Returning 200 OK.") # Debug print
    return HttpResponse(status=200)
