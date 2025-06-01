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
        return HttpResponse(status=200) # Event already processed or failed to save, return 200 to Stripe

    # 3. Process the event based on its type
    event_type = event['type']
    event_data = event['data']['object']
    print(f"DEBUG: Processing event type: {event_type}") # Debug print

    # Determine the relevant ID for lookup based on event type
    # For 'charge.refunded', the event_data is the Charge object, which has a payment_intent.
    # For 'payment_intent.succeeded', the event_data is the PaymentIntent object.
    if event_type.startswith('payment_intent.'):
        lookup_id = event_data.get('id')
        lookup_field = 'stripe_payment_intent_id'
    elif event_type.startswith('charge.'):
        # For charge events, the relevant ID is often the payment_intent associated with the charge
        lookup_id = event_data.get('payment_intent')
        lookup_field = 'stripe_payment_intent_id'
    else:
        print(f"WARNING: Unhandled event type: {event_type}. Returning 200.") # Debug print
        return HttpResponse(status=200)

    print(f"DEBUG: Looking up Payment object using {lookup_field}={lookup_id}") # Debug print

    try:
        with transaction.atomic():
            payment_obj = Payment.objects.select_for_update().get(**{lookup_field: lookup_id})
            print(f"DEBUG: Payment object found: {payment_obj.id}") # Debug print

            # Update Payment object status if different
            if payment_obj.status != event_data.get('status', payment_obj.status): # Use .get with default for safety
                payment_obj.status = event_data.get('status', payment_obj.status)
                # For charge.refunded, amount might not be directly on event_data object, but on refunds sub-object
                # For simplicity, we'll keep the amount update primarily for payment_intent.succeeded
                # and let the handler for charge.refunded manage refunded_amount.
                if 'amount' in event_data: # Only update amount if present in event_data (e.g., payment_intent.succeeded)
                    payment_obj.amount = Decimal(event_data['amount']) / Decimal('100')
                if 'currency' in event_data:
                    payment_obj.currency = event_data['currency'].upper()
                payment_obj.save()
                print(f"DEBUG: Updated Payment {payment_obj.id} status to {payment_obj.status}.") # Debug print

            # 4. Dispatch to specific business logic handler
            # For 'charge.refunded', the metadata might be on the original PaymentIntent,
            # or it might be passed through to the Charge.
            # We'll try to get it from the Payment object's associated booking if available,
            # or from the event_data's metadata if it's a PaymentIntent event.
            booking_type = None
            if payment_obj.hire_booking:
                booking_type = 'hire_booking' # Assume hire_booking if linked
            elif event_type.startswith('payment_intent.'):
                booking_type = event_data.get('metadata', {}).get('booking_type')

            print(f"DEBUG: Determined booking_type: {booking_type} for event type: {event_type}") # Debug print

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
                    print(f"WARNING: No handler found for booking_type '{booking_type}' and event type '{event_type}'.") # Debug print
            else:
                print(f"WARNING: No booking_type determined or booking_type '{booking_type}' not in WEBHOOK_HANDLERS.") # Debug print

    except Payment.DoesNotExist:
        print(f"WARNING: Payment object with {lookup_field}={lookup_id} not found. Returning 200.") # Debug print
        return HttpResponse(status=200) # Payment not found, likely an old or irrelevant event, acknowledge
    except Exception as e:
        print(f"CRITICAL ERROR: Unexpected error during webhook processing for event type {event_type}: {e}") # Debug print
        return HttpResponse(status=500) # Something went wrong, tell Stripe to retry

    # Always return a 200 OK to Stripe to acknowledge receipt
    print(f"DEBUG: Webhook processing complete for event type: {event_type}. Returning 200.") # Debug print
    return HttpResponse(status=200)
