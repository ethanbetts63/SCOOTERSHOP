from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.db import transaction
from django.utils import timezone
import stripe
from decimal import Decimal
from payments.models import Payment, WebhookEvent
from payments.webhook_handlers import WEBHOOK_HANDLERS


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    event = None


    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)
    except Exception:
        return HttpResponse(status=400)

    try:
        with transaction.atomic():
            WebhookEvent.objects.create(
                stripe_event_id=event["id"],
                event_type=event["type"],
                payload=event.to_dict(),
                received_at=timezone.now(),
            )
    except Exception:
        return HttpResponse(status=200)

    event_type = event["type"]
    event_data = event["data"]["object"]

    lookup_id = None
    lookup_field = "stripe_payment_intent_id"

    if event_type.startswith("payment_intent."):
        lookup_id = event_data.get("id")
    elif event_type.startswith("charge."):
        lookup_id = event_data.get("payment_intent")
    else:
        return HttpResponse(status=200)

    if not lookup_id:
        return HttpResponse(status=200)

    if event_type.startswith("payment_intent.") or event_type.startswith("charge."):
        try:
            with transaction.atomic():
                payment_obj = Payment.objects.select_for_update().get(
                    **{lookup_field: lookup_id}
                )

                if (
                    event_type.startswith("payment_intent.")
                    and payment_obj.status != event_data["status"]
                ):
                    payment_obj.status = event_data["status"]
                    if "amount" in event_data:
                        payment_obj.amount = Decimal(event_data["amount"]) / Decimal(
                            "100"
                        )
                    if "currency" in event_data:
                        payment_obj.currency = event_data["currency"].upper()
                    payment_obj.save()

                booking_type = None

                if payment_obj.service_booking or payment_obj.temp_service_booking:
                    booking_type = "service_booking"
                elif payment_obj.sales_booking or payment_obj.temp_sales_booking:
                    booking_type = "sales_booking"
                elif (
                    "metadata" in event_data
                    and "booking_type" in event_data["metadata"]
                ):
                    booking_type = event_data["metadata"]["booking_type"]
                else:
                    pass

                if booking_type and booking_type in WEBHOOK_HANDLERS:
                    handler = WEBHOOK_HANDLERS[booking_type].get(event_type)
                    if handler:
                        try:
                            handler(payment_obj, event_data)
                        except Exception:
                            raise
                    else:
                        pass
                else:
                    pass

        except Payment.DoesNotExist:
            return HttpResponse(status=200)
        except Exception:
            return HttpResponse(status=500)
    else:
        pass

    return HttpResponse(status=200)
