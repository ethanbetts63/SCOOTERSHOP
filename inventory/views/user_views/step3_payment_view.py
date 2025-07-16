import logging

logger = logging.getLogger(__name__)
from django.views import View
from django.http import JsonResponse, Http404
from django.conf import settings
from django.urls import reverse
from django.contrib import messages
import stripe
import json
from payments.models import Payment
from inventory.models import TempSalesBooking, InventorySettings, Motorcycle
from inventory.utils.create_update_sales_payment_intent import (
    create_or_update_sales_payment_intent,
)
from decimal import Decimal

stripe.api_key = settings.STRIPE_SECRET_KEY


class Step3PaymentView(View):

    def get(self, request, *args, **kwargs):
        temp_booking_uuid = request.session.get("temp_sales_booking_uuid")

        if not temp_booking_uuid:
            messages.error(request, "Your booking session has expired or is invalid.")
            return redirect("inventory:used")

        try:
            temp_booking = get_object_or_404(
                TempSalesBooking, session_uuid=temp_booking_uuid
            )
        except Http404:
            logger.warning(
                f"Step3 GET: TempSalesBooking not found for uuid {temp_booking_uuid}."
            )
            messages.error(request, "Your booking session could not be found.")
            return redirect("inventory:used")
        except Exception as e:
            logger.error(
                f"Step3 GET: Error retrieving TempSalesBooking with uuid {temp_booking_uuid}. Error: {e}"
            )
            messages.error(
                request, "An unexpected error occurred while retrieving your booking."
            )
            return redirect("inventory:used")

        if not temp_booking.motorcycle:
            messages.error(request, "Please select a motorcycle first.")
            return redirect("inventory:used")

        if not temp_booking.sales_profile:
            messages.error(request, "Please provide your contact details first.")
            return redirect("inventory:step2_booking_details_and_appointment")

        try:
            inventory_settings = InventorySettings.objects.get()
        except InventorySettings.DoesNotExist:
            logger.error("Step3 GET: InventorySettings not configured.")
            messages.error(
                request,
                "Inventory settings are not configured. Please contact support.",
            )
            return redirect("inventory:used")

        if not temp_booking.deposit_required_for_flow:
            messages.warning(
                request,
                "Payment is not required for this type of booking. Redirecting to confirmation.",
            )
            redirect_url = (
                reverse("inventory:step4_confirmation")
                + f'?payment_intent_id={temp_booking.stripe_payment_intent_id if temp_booking.stripe_payment_intent_id else ""}'
            )
            return redirect(redirect_url)

        try:
            motorcycle = Motorcycle.objects.get(pk=temp_booking.motorcycle.pk)
            if not motorcycle.is_available:
                messages.error(
                    request,
                    "Sorry, this motorcycle has just been reserved or sold and is no longer available.",
                )
                return redirect(reverse("inventory:used"))
        except Motorcycle.DoesNotExist:
            messages.error(request, "The selected motorcycle could not be found.")
            return redirect(reverse("inventory:used"))

        currency = inventory_settings.currency_code

        amount_to_pay = temp_booking.amount_paid

        if amount_to_pay is None or amount_to_pay <= 0:
            messages.error(
                request,
                "The amount to pay is invalid. Please review your booking details.",
            )
            return redirect("inventory:step2_booking_details_and_appointment")

        sales_customer_profile = temp_booking.sales_profile
        payment_obj = Payment.objects.filter(temp_sales_booking=temp_booking).first()

        try:
            intent, payment_obj = create_or_update_sales_payment_intent(
                temp_booking=temp_booking,
                sales_profile=sales_customer_profile,
                amount_to_pay=amount_to_pay,
                currency=currency,
                existing_payment_obj=payment_obj,
            )

        except stripe.error.StripeError as e:
            logger.error(
                f"Step3 GET: Stripe error for temp_booking {temp_booking.id}. Error: {e}"
            )
            messages.error(
                request, f"Payment system error: {e}. Please try again later."
            )
            return redirect("inventory:step2_booking_details_and_appointment")
        except Exception as e:
            logger.error(
                f"Step3 GET: Unexpected error during payment setup for temp_booking {temp_booking.id}. Error: {e}"
            )
            messages.error(
                request,
                "An unexpected error occurred during payment setup. Please try again.",
            )
            return redirect("inventory:step2_booking_details_and_appointment")

        if not intent:
            messages.error(request, "Could not set up payment. Please try again.")
            return redirect("inventory:step2_booking_details_and_appointment")

        amount_remaining = Decimal("0.00")
        if temp_booking.motorcycle and temp_booking.motorcycle.price is not None:
            amount_remaining = temp_booking.motorcycle.price - amount_to_pay

        context = {
            "client_secret": intent.client_secret,
            "amount": amount_to_pay,
            "currency": currency.upper(),
            "temp_booking": temp_booking,
            "stripe_publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
            "amount_remaining": amount_remaining,
        }
        return render(request, "inventory/step3_payment.html", context)

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            payment_intent_id = data.get("payment_intent_id")
        except json.JSONDecodeError:
            logger.error("Step3 POST: Invalid JSON format in request body.")
            return JsonResponse(
                {"error": "Invalid JSON format in request body"}, status=400
            )

        if not payment_intent_id:
            return JsonResponse(
                {"error": "Payment Intent ID is required in the request"}, status=400
            )

        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)

            if intent.status == "succeeded":
                return JsonResponse(
                    {
                        "status": "success",
                        "message": "Payment processed successfully. Your booking is being finalized.",
                        "redirect_url": reverse("inventory:step4_confirmation")
                        + f"?payment_intent_id={payment_intent_id}",
                    }
                )

            elif intent.status in [
                "requires_action",
                "requires_confirmation",
                "requires_payment_method",
                "processing",
            ]:
                return JsonResponse(
                    {
                        "status": "requires_action",
                        "message": "Payment requires further action or is pending. Please follow prompts provided by Stripe.",
                    }
                )

            else:
                return JsonResponse(
                    {
                        "status": "failed",
                        "message": "Payment failed or an unexpected status occurred. Please try again.",
                    }
                )

        except stripe.error.StripeError as e:
            logger.error(f"Step3 POST: Stripe error on payment intent retrieval. Error: {e}")
            return JsonResponse({"error": str(e)}, status=500)
        except Exception as e:
            logger.error(f"Step3 POST: Internal server error on payment processing. Error: {e}")
            return JsonResponse(
                {
                    "error": "An internal server error occurred during payment processing."
                },
                status=500,
            )
