import stripe
from django.shortcuts import redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.db import transaction
from django.conf import settings
from decimal import Decimal
from django.utils import timezone

from core.mixins import AdminRequiredMixin
from payments.models import RefundRequest


class ProcessRefundView(AdminRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        refund_request = get_object_or_404(RefundRequest, pk=pk)

        admin_management_redirect_url = "payments:admin_refund_management"

        if refund_request.status not in [
            "pending",
            "reviewed_pending_approval",
            "unverified",
            "approved",
        ]:
            messages.error(
                request,
                f"Refund request is not in an approvable state. Current status: {refund_request.get_status_display()}.",
            )
            return redirect(admin_management_redirect_url)

        if not refund_request.payment:
            messages.error(
                request,
                "Cannot process refund: No associated payment found for this request.",
            )
            return redirect(admin_management_redirect_url)

        if (
            refund_request.amount_to_refund is None
            or refund_request.amount_to_refund <= 0
        ):
            messages.error(
                request, "Cannot process refund: No valid amount specified to refund."
            )
            return redirect(admin_management_redirect_url)

        if not refund_request.payment.stripe_payment_intent_id:
            messages.error(
                request,
                "Cannot process refund: Associated payment has no Stripe Payment Intent ID.",
            )
            return redirect(admin_management_redirect_url)

        stripe.api_key = settings.STRIPE_SECRET_KEY

        try:
            with transaction.atomic():
                amount_in_cents = int(refund_request.amount_to_refund * Decimal("100"))

                booking_reference_for_metadata = "N/A"
                booking_type_for_metadata = "unknown"
                if refund_request.service_booking:
                    booking_reference_for_metadata = (
                        refund_request.service_booking.service_booking_reference
                    )
                    booking_type_for_metadata = "service"
                elif refund_request.sales_booking:
                    booking_reference_for_metadata = (
                        refund_request.sales_booking.sales_booking_reference
                    )
                    booking_type_for_metadata = "sales"

                metadata = {
                    "refund_request_id": str(refund_request.pk),
                    "admin_user_id": str(request.user.pk),
                    "booking_reference": booking_reference_for_metadata,
                    "booking_type": booking_type_for_metadata,
                }

                stripe_refund = stripe.Refund.create(
                    payment_intent=refund_request.payment.stripe_payment_intent_id,
                    amount=amount_in_cents,
                    reason="requested_by_customer",
                    metadata=metadata,
                )

                refund_request.status = "approved"
                if not refund_request.processed_by:
                    refund_request.processed_by = request.user
                    refund_request.processed_at = timezone.now()
                refund_request.stripe_refund_id = stripe_refund.id
                refund_request.save()

                messages.success(
                    request,
                    f"Refund request for booking '{booking_reference_for_metadata}' has been approved and initiated with Stripe (ID: {stripe_refund.id}). Awaiting final confirmation from Stripe.",
                )
                return redirect(admin_management_redirect_url)

        except stripe.error.StripeError as e:
            error_message = f"Stripe error initiating refund: {e.user_message or e}"
            messages.error(request, error_message)
            refund_request.status = "failed"
            refund_request.staff_notes = (
                (refund_request.staff_notes or "")
                + f"\nStripe initiation failed: {e.user_message or e} at {timezone.now()}"
            )
            refund_request.save()
            return redirect(admin_management_redirect_url)
        except Exception as e:
            error_message = f"An unexpected error occurred: {e}"
            messages.error(request, error_message)
            refund_request.status = "failed"
            refund_request.staff_notes = (
                refund_request.staff_notes or ""
            ) + f"\nUnexpected error during initiation: {e} at {timezone.now()}"
            refund_request.save()
            return redirect(admin_management_redirect_url)
