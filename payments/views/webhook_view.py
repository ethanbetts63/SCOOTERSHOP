from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.db import transaction
from django.utils import timezone
import stripe
import json

from payments.models import Payment, WebhookEvent
from payments.webhook_handlers import WEBHOOK_HANDLERS

@csrf_exempt
def stripe_webhook(request):
    print("DEBUG: ===== STRIPE WEBHOOK HIT AT VERY BEGINNING =====") # ULTRA DEBUG PRINT

    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
        print(f"DEBUG: stripe_webhook - Webhook event constructed successfully. Type: {event['type']}")
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        print(f"ERROR: stripe_webhook - Signature verification failed or invalid payload: {e}")
        return HttpResponse(status=400)
    except Exception as e:
        print(f"ERROR: stripe_webhook - Unexpected error during event construction: {e}")
        return HttpResponse(status=400)

    try:
        with transaction.atomic():
            WebhookEvent.objects.create(
                stripe_event_id=event['id'],
                event_type=event['type'],
                payload=event.to_dict(),
                received_at=timezone.now()
            )
        print(f"DEBUG: stripe_webhook - WebhookEvent recorded: {event['id']} ({event['type']})")
    except Exception as e:
        print(f"ERROR: stripe_webhook - Failed to record WebhookEvent: {e}")
        # Return 200 even if recording fails to avoid Stripe retries for already processed events
        return HttpResponse(status=200)

    event_type = event['type']
    event_data = event['data']['object']

    lookup_id = None
    lookup_field = 'stripe_payment_intent_id'

    if event_type.startswith('payment_intent.'):
        lookup_id = event_data.get('id')
        print(f"DEBUG: stripe_webhook - Event type is payment_intent. Lookup ID: {lookup_id}")
    elif event_type.startswith('charge.'):
        lookup_id = event_data.get('payment_intent')
        print(f"DEBUG: stripe_webhook - Event type is charge. Lookup ID: {lookup_id}")
    else:
        print(f"DEBUG: stripe_webhook - Unhandled event type: {event_type}. Returning 200.")
        return HttpResponse(status=200)

    if not lookup_id:
        print(f"DEBUG: stripe_webhook - No lookup_id found for event type {event_type}. Returning 200.")
        return HttpResponse(status=200)

    if event_type.startswith('payment_intent.') or event_type.startswith('charge.'):
        try:
            with transaction.atomic():
                print(f"DEBUG: stripe_webhook - Attempting to retrieve Payment object with {lookup_field}={lookup_id}")
                payment_obj = Payment.objects.select_for_update().get(**{lookup_field: lookup_id})
                print(f"DEBUG: stripe_webhook - Payment object found: {payment_obj.id}")

                if event_type.startswith('payment_intent.') and payment_obj.status != event_data['status']:
                    print(f"DEBUG: stripe_webhook - Updating Payment status from {payment_obj.status} to {event_data['status']}")
                    payment_obj.status = event_data['status']
                    if 'amount' in event_data:
                        payment_obj.amount = Decimal(event_data['amount']) / Decimal('100')
                        print(f"DEBUG: stripe_webhook - Updated payment_obj.amount to: {payment_obj.amount}")
                    if 'currency' in event_data:
                        payment_obj.currency = event_data['currency'].upper()
                        print(f"DEBUG: stripe_webhook - Updated payment_obj.currency to: {payment_obj.currency}")
                    payment_obj.save()
                    print("DEBUG: stripe_webhook - Payment object saved after status/amount/currency update.")

                booking_type = None
                if payment_obj.hire_booking:
                    booking_type = 'hire_booking'
                    print("DEBUG: stripe_webhook - Detected booking_type: hire_booking (from payment_obj.hire_booking)")
                elif payment_obj.temp_hire_booking:
                    booking_type = 'hire_booking'
                    print("DEBUG: stripe_webhook - Detected booking_type: hire_booking (from payment_obj.temp_hire_booking)")
                elif payment_obj.service_booking:
                    booking_type = 'service_booking'
                    print("DEBUG: stripe_webhook - Detected booking_type: service_booking (from payment_obj.service_booking)")
                elif payment_obj.temp_service_booking:
                    booking_type = 'service_booking'
                    print("DEBUG: stripe_webhook - Detected booking_type: service_booking (from payment_obj.temp_service_booking)")
                elif 'metadata' in event_data and 'booking_type' in event_data['metadata']:
                    booking_type = event_data['metadata']['booking_type']
                    print(f"DEBUG: stripe_webhook - Detected booking_type: {booking_type} (from metadata)")
                else:
                    print("DEBUG: stripe_webhook - No specific booking_type detected.")
                    pass

                if booking_type and booking_type in WEBHOOK_HANDLERS:
                    print(f"DEBUG: stripe_webhook - Found booking_type '{booking_type}' in WEBHOOK_HANDLERS.")
                    handler = WEBHOOK_HANDLERS[booking_type].get(event_type)
                    if handler:
                        print(f"DEBUG: stripe_webhook - Found handler for event_type '{event_type}'. Attempting to call handler.")
                        try:
                            handler(payment_obj, event_data)
                            print("DEBUG: stripe_webhook - Handler executed successfully.")
                        except Exception as handler_e:
                            print(f"ERROR: stripe_webhook - Exception during handler execution: {handler_e}")
                            raise # Re-raise to ensure transaction rollback
                    else:
                        print(f"DEBUG: stripe_webhook - No handler found for event_type '{event_type}' under booking_type '{booking_type}'.")
                        pass
                else:
                    print(f"DEBUG: stripe_webhook - Booking type '{booking_type}' not found in WEBHOOK_HANDLERS or is None.")
                    pass

        except Payment.DoesNotExist:
            print(f"DEBUG: stripe_webhook - Payment object with {lookup_field}={lookup_id} not found. This might be expected for some events.")
            return HttpResponse(status=200) # It's common to receive webhooks for payments not yet in your DB
        except Exception as e:
            print(f"ERROR: stripe_webhook - An unexpected error occurred within the transaction block: {e}")
            return HttpResponse(status=500)
    else:
        print(f"DEBUG: stripe_webhook - Event type {event_type} not handled in the main processing block.")
        pass # This block might be for other event types not requiring payment object lookup

    print("DEBUG: stripe_webhook - Webhook view exited successfully.")
    return HttpResponse(status=200)
