import logging

logger = logging.getLogger(__name__)
from django.views import View
from django.contrib import messages
from decimal import Decimal
from inventory.models import SalesBooking
from payments.models import Payment
from inventory.utils.booking_protection import set_recent_booking_flag
from inventory.utils.get_sales_faqs import get_faqs_for_step


class Step4ConfirmationView(View):
    def get(self, request):
        sales_booking = None
        is_processing = False

        booking_reference = request.session.get("current_sales_booking_reference")
        if booking_reference:
            try:
                sales_booking = SalesBooking.objects.get(
                    sales_booking_reference=booking_reference
                )
            except SalesBooking.DoesNotExist:
                logger.warning(
                    f"Step4 GET: SalesBooking not found for booking_reference {booking_reference}."
                )
                del request.session["current_sales_booking_reference"]
                pass

        payment_intent_id = request.GET.get("payment_intent_id")
        if not sales_booking and payment_intent_id:
            try:
                sales_booking = SalesBooking.objects.get(
                    stripe_payment_intent_id=payment_intent_id
                )
                request.session["current_sales_booking_reference"] = (
                    sales_booking.sales_booking_reference
                )
                is_processing = False

            except SalesBooking.DoesNotExist:
                try:
                    Payment.objects.get(stripe_payment_intent_id=payment_intent_id)
                    is_processing = True
                except Payment.DoesNotExist:
                    logger.warning(
                        f"Step4 GET: Payment not found for payment_intent_id {payment_intent_id} after SalesBooking miss."
                    )
                    is_processing = False
            except Exception as e:
                logger.error(
                    f"Step4 GET: Error retrieving SalesBooking with payment_intent_id {payment_intent_id}. Error: {e}"
                )
                try:
                    Payment.objects.get(stripe_payment_intent_id=payment_intent_id)
                    is_processing = True
                except Payment.DoesNotExist:
                    logger.warning(
                        f"Step4 GET: Payment not found for payment_intent_id {payment_intent_id} after exception. Error: {e}"
                    )
                    is_processing = False

        if sales_booking:
            if "temp_sales_booking_uuid" in request.session:
                del request.session["temp_sales_booking_uuid"]

            set_recent_booking_flag(request)

            amount_owing = Decimal("0.00")
            if sales_booking.motorcycle and sales_booking.motorcycle.price is not None:
                amount_owing = (
                    sales_booking.motorcycle.price - sales_booking.amount_paid
                )

            if amount_owing < Decimal("0.00"):
                amount_owing = Decimal("0.00")

            context = {
                "sales_booking": sales_booking,
                "booking_status": sales_booking.get_booking_status_display(),
                "payment_status": sales_booking.get_payment_status_display(),
                "amount_paid": sales_booking.amount_paid,
                "currency": sales_booking.currency,
                "motorcycle_details": f"{sales_booking.motorcycle.year} {sales_booking.motorcycle.brand} {sales_booking.motorcycle.model}",
                "customer_name": sales_booking.sales_profile.name,
                "is_processing": False,
                "motorcycle_price": sales_booking.motorcycle.price,
                "amount_owing": amount_owing,
                "sales_faqs": get_faqs_for_step("step4"),
                "faq_title": "What Happens Next?",
            }
            return render(request, "inventory/step4_confirmation.html", context)

        elif is_processing and payment_intent_id:
            context = {
                "is_processing": True,
                "payment_intent_id": payment_intent_id,
            }
            return render(request, "inventory/step4_confirmation.html", context)
        else:
            messages.warning(
                request,
                "Could not find a booking confirmation. Please start over if you have not booked.",
            )
            return redirect("inventory:used")
