# payments/views/webhook_view.py
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.db import transaction
from django.utils import timezone
import stripe
import json

from payments.models import Payment, WebhookEvent
from payments.webhook_handlers import WEBHOOK_HANDLERS # Import the handlers dictionary


@csrf_exempt
def stripe_webhook(request):
    """
    Stripe webhook endpoint for receiving and processing payment events.
    This view is generic and dispatches specific business logic to handlers
    based on metadata in the PaymentIntent.
    """
    print("DEBUG: Stripe webhook received.") # Debug print

    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    event = None

    # 1. Verify Stripe Signature
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
        print(f"DEBUG: Webhook signature verified for event ID: {event['id']}") # Debug print
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        print(f"ERROR: Webhook signature verification failed: {e}") # Debug print
        return HttpResponse(status=400)
    except Exception as e:
        print(f"CRITICAL ERROR: Unexpected error during webhook signature verification: {e}") # Debug print
        return HttpResponse(status=400)

    # 2. Idempotency Check: Record the event and check if already processed
    try:
        with transaction.atomic():
            WebhookEvent.objects.create(
                stripe_event_id=event['id'],
                event_type=event['type'],
                payload=event.to_dict(),
                received_at=timezone.now()
            )
            print(f"DEBUG: WebhookEvent {event['id']} recorded successfully.") # Debug print
    except Exception as e:
        print(f"WARNING: WebhookEvent {event['id']} already processed or failed to record: {e}. Returning 200.") # Debug print
        return HttpResponse(status=200)

    # 3. Process the event based on its type
    event_type = event['type']
    event_data = event['data']['object']
    payment_intent_id = event_data.get('id')
    print(f"DEBUG: Processing event type: {event_type}") # Debug print
    print(f"DEBUG: Event data object ID: {payment_intent_id}") # Debug print

    # Handle PaymentIntent-related events
    if event_type.startswith('payment_intent.'):
        print(f"DEBUG: Event type starts with 'payment_intent.'. Attempting to find Payment object.") # Debug print
        try:
            with transaction.atomic():
                print(f"DEBUG: Looking up Payment object with stripe_payment_intent_id={payment_intent_id}") # Debug print
                payment_obj = Payment.objects.select_for_update().get(stripe_payment_intent_id=payment_intent_id)
                print(f"DEBUG: Payment object found: {payment_obj.id}") # Debug print

                if payment_obj.status != event_data['status']:
                    print(f"DEBUG: Updating Payment {payment_obj.id} status from {payment_obj.status} to {event_data['status']}.") # Debug print
                    payment_obj.status = event_data['status']
                    payment_obj.amount = event_data['amount'] / 100
                    payment_obj.currency = event_data['currency'].upper()
                    payment_obj.save()
                    print(f"DEBUG: Payment {payment_obj.id} updated.") # Debug print

                # 4. Dispatch to specific business logic handler
                booking_type = event_data.get('metadata', {}).get('booking_type')
                print(f"DEBUG: Determined booking_type: {booking_type}") # Debug print

                if booking_type and booking_type in WEBHOOK_HANDLERS:
                    handler = WEBHOOK_HANDLERS[booking_type].get(event_type)
                    if handler:
                        print(f"DEBUG: Dispatching to handler: {handler.__name__}") # Debug print
                        try:
                            handler(payment_obj, event_data)
                            print(f"DEBUG: Handler {handler.__name__} executed successfully.") # Debug print
                        except Exception as handler_e:
                            print(f"CRITICAL ERROR: Error in webhook handler {handler.__name__}: {handler_e}") # Debug print
                            raise  # Re-raise to trigger the outer 500 response
                    else:
                        print(f"WARNING: No specific handler found for booking_type '{booking_type}' and event type '{event_type}'.") # Debug print
                else:
                    print(f"WARNING: Booking type '{booking_type}' not found or not in WEBHOOK_HANDLERS for event type '{event_type}'.") # Debug print

        except Payment.DoesNotExist:
            print(f"WARNING: Payment object with stripe_payment_intent_id={payment_intent_id} not found. Returning 200.") # Debug print
            return HttpResponse(status=200)
        except Exception as e:
            print(f"CRITICAL ERROR: Unexpected error during PaymentIntent event processing for ID {payment_intent_id}: {e}") # Debug print
            return HttpResponse(status=500)
    else:
        print(f"WARNING: Event type '{event_type}' is not a 'payment_intent.' event. No specific handler dispatched by this block.") # Debug print


    # Always return a 200 OK to Stripe to acknowledge receipt
    print(f"DEBUG: Webhook processing complete for event ID: {event['id']}. Returning 200.") # Debug print
    return HttpResponse(status=200)
