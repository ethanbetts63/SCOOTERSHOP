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

    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    event = None

    # 1. Verify Stripe Signature
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)
    except Exception:
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
    except Exception:
        return HttpResponse(status=200)

    # 3. Process the event based on its type
    event_type = event['type']
    event_data = event['data']['object']
    payment_intent_id = event_data.get('id')

    # Handle PaymentIntent-related events
    if event_type.startswith('payment_intent.'):
        try:
            with transaction.atomic():
                payment_obj = Payment.objects.select_for_update().get(stripe_payment_intent_id=payment_intent_id)

                if payment_obj.status != event_data['status']:
                    payment_obj.status = event_data['status']
                    payment_obj.amount = event_data['amount'] / 100
                    payment_obj.currency = event_data['currency'].upper()
                    payment_obj.save()

                # 4. Dispatch to specific business logic handler
                booking_type = event_data.get('metadata', {}).get('booking_type')

                if booking_type and booking_type in WEBHOOK_HANDLERS:
                    handler = WEBHOOK_HANDLERS[booking_type].get(event_type)
                    if handler:
                        try:
                            handler(payment_obj, event_data)
                        except Exception:
                            raise  # Re-raise to trigger the outer 500 response

        except Payment.DoesNotExist:
            return HttpResponse(status=200)
        except Exception:
            return HttpResponse(status=500)
    # No else block needed as we handle all cases

    # Always return a 200 OK to Stripe to acknowledge receipt
    return HttpResponse(status=200)