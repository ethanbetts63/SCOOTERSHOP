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
    print(f"DEBUG: Processing event type: {event_type}") # Debug print

    # Determine the correct ID for Payment lookup based on event type
    lookup_id = None
    lookup_field = 'stripe_payment_intent_id' # Default lookup field

    if event_type.startswith('payment_intent.'):
        lookup_id = event_data.get('id')
        print(f"DEBUG: Event type is 'payment_intent.'. Using event_data['id'] as lookup_id: {lookup_id}")
    elif event_type.startswith('charge.'):
        # For charge events (like charge.refunded), the payment intent ID is under 'payment_intent'
        lookup_id = event_data.get('payment_intent')
        print(f"DEBUG: Event type is 'charge.'. Using event_data['payment_intent'] as lookup_id: {lookup_id}")
    else:
        print(f"WARNING: Event type '{event_type}' is not directly handled for Payment lookup. Returning 200.")
        return HttpResponse(status=200) # Unhandled event type, acknowledge

    if not lookup_id:
        print(f"WARNING: No lookup ID found for event type '{event_type}'. Cannot find associated Payment. Returning 200.")
        return HttpResponse(status=200)

    # Handle PaymentIntent-related and Charge-related events
    # The original condition was `if event_type.startswith('payment_intent.')`
    # We now extend it to include 'charge.' events.
    if event_type.startswith('payment_intent.') or event_type.startswith('charge.'):
        print(f"DEBUG: Event type starts with 'payment_intent.' or 'charge.'. Attempting to find Payment object.")
        try:
            with transaction.atomic():
                print(f"DEBUG: Looking up Payment object with {lookup_field}={lookup_id}")
                payment_obj = Payment.objects.select_for_update().get(**{lookup_field: lookup_id})
                print(f"DEBUG: Payment object found: {payment_obj.id}")

                # Update Payment object status if different (primarily for payment_intent.succeeded)
                # For charge.refunded, the handler will manage refunded_amount and final status.
                if event_type.startswith('payment_intent.') and payment_obj.status != event_data['status']:
                    print(f"DEBUG: Updating Payment {payment_obj.id} status from {payment_obj.status} to {event_data['status']}.")
                    payment_obj.status = event_data['status']
                    # Only update amount/currency if present in event_data (e.g., payment_intent.succeeded)
                    if 'amount' in event_data:
                        payment_obj.amount = event_data['amount'] / 100
                    if 'currency' in event_data:
                        payment_obj.currency = event_data['currency'].upper()
                    payment_obj.save()
                    print(f"DEBUG: Payment {payment_obj.id} updated.")

                # 4. Dispatch to specific business logic handler
                # Determine booking_type, prioritizing from linked HireBooking if available
                booking_type = None
                if payment_obj.hire_booking:
                    booking_type = 'hire_booking'
                    print(f"DEBUG: Determined booking_type from linked HireBooking: {booking_type}")
                elif 'metadata' in event_data and 'booking_type' in event_data['metadata']:
                    booking_type = event_data['metadata']['booking_type']
                    print(f"DEBUG: Determined booking_type from event metadata: {booking_type}")
                else:
                    print(f"WARNING: Could not determine booking_type for event type '{event_type}'.")


                if booking_type and booking_type in WEBHOOK_HANDLERS:
                    handler = WEBHOOK_HANDLERS[booking_type].get(event_type)
                    if handler:
                        print(f"DEBUG: Dispatching to handler: {handler.__name__}")
                        try:
                            handler(payment_obj, event_data)
                            print(f"DEBUG: Handler {handler.__name__} executed successfully.")
                        except Exception as handler_e:
                            print(f"CRITICAL ERROR: Error in webhook handler {handler.__name__}: {handler_e}")
                            raise  # Re-raise to trigger the outer 500 response
                    else:
                        print(f"WARNING: No specific handler found for booking_type '{booking_type}' and event type '{event_type}'.")
                else:
                    print(f"WARNING: Booking type '{booking_type}' not found or not in WEBHOOK_HANDLERS for event type '{event_type}'.")

        except Payment.DoesNotExist:
            print(f"WARNING: Payment object with {lookup_field}={lookup_id} not found. Returning 200.")
            return HttpResponse(status=200)
        except Exception as e:
            print(f"CRITICAL ERROR: Unexpected error during webhook processing for ID {lookup_id}, event type {event_type}: {e}")
            return HttpResponse(status=500)
    else:
        print(f"WARNING: Event type '{event_type}' is not a 'payment_intent.' or 'charge.' event. No specific handler dispatched by this block.")


    # Always return a 200 OK to Stripe to acknowledge receipt
    print(f"DEBUG: Webhook processing complete for event ID: {event['id']}. Returning 200.")
    return HttpResponse(status=200)
