import stripe
from django.shortcuts import redirect, get_object_or_404
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.db import transaction
from django.conf import settings
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth.decorators import user_passes_test
from users.views.auth import is_admin
from payments.models import RefundRequest


@method_decorator(user_passes_test(is_admin), name='dispatch')
class ProcessRefundView(View):
    def post(self, request, pk, *args, **kwargs):
        print(f"DEBUG: Entering ProcessRefundView.post for RefundRequest PK: {pk}")
        refund_request = get_object_or_404(RefundRequest, pk=pk)
        print(f"DEBUG: Retrieved RefundRequest. Current status: {refund_request.status}")

        admin_management_redirect_url = 'payments:admin_refund_management'

        if refund_request.status not in ['pending', 'reviewed_pending_approval', 'unverified']:
            print(f"DEBUG: Refund request status '{refund_request.get_status_display()}' is not approvable.")
            messages.error(request, f"Refund request is not in an approvable state. Current status: {refund_request.get_status_display()}.")
            return redirect(admin_management_redirect_url)

        if not refund_request.payment:
            print("DEBUG: No associated payment found for this request.")
            messages.error(request, "Cannot process refund: No associated payment found for this request.")
            return redirect(admin_management_redirect_url)
        print(f"DEBUG: Payment found. Payment ID: {refund_request.payment.id}, Amount: {refund_request.payment.amount}, Status: {refund_request.payment.status}")


        if refund_request.amount_to_refund is None or refund_request.amount_to_refund <= 0:
            print(f"DEBUG: Invalid amount to refund: {refund_request.amount_to_refund}")
            messages.error(request, "Cannot process refund: No valid amount specified to refund.")
            return redirect(admin_management_redirect_url)
        print(f"DEBUG: Amount to refund: {refund_request.amount_to_refund}")

        if not refund_request.payment.stripe_payment_intent_id:
            print("DEBUG: Associated payment has no Stripe Payment Intent ID.")
            messages.error(request, "Cannot process refund: Associated payment has no Stripe Payment Intent ID.")
            return redirect(admin_management_redirect_url)
        print(f"DEBUG: Stripe Payment Intent ID: {refund_request.payment.stripe_payment_intent_id}")


        stripe.api_key = settings.STRIPE_SECRET_KEY

        try:
            with transaction.atomic():
                amount_in_cents = int(refund_request.amount_to_refund * Decimal('100'))
                print(f"DEBUG: Amount in cents for Stripe: {amount_in_cents}")

                booking_reference_for_metadata = "N/A"
                booking_type_for_metadata = "unknown"

                if refund_request.hire_booking:
                    booking_reference_for_metadata = refund_request.hire_booking.booking_reference
                    booking_type_for_metadata = 'hire'
                elif refund_request.service_booking:
                    booking_reference_for_metadata = refund_request.service_booking.service_booking_reference
                    booking_type_for_metadata = 'service'
                elif refund_request.sales_booking:
                    booking_reference_for_metadata = refund_request.sales_booking.sales_booking_reference
                    booking_type_for_metadata = 'sales'
                print(f"DEBUG: Booking ref for metadata: {booking_reference_for_metadata}, Type: {booking_type_for_metadata}")

                metadata = {
                    'refund_request_id': str(refund_request.pk),
                    'admin_user_id': str(request.user.pk),
                    'booking_reference': booking_reference_for_metadata,
                    'booking_type': booking_type_for_metadata,
                }
                print(f"DEBUG: Stripe Refund metadata: {metadata}")

                print("DEBUG: Calling stripe.Refund.create()...")
                stripe_refund = stripe.Refund.create(
                    payment_intent=refund_request.payment.stripe_payment_intent_id,
                    amount=amount_in_cents,
                    reason='requested_by_customer',
                    metadata=metadata
                )
                print(f"DEBUG: stripe.Refund.create() successful. Stripe Refund ID: {stripe_refund.id}")

                refund_request.status = 'approved'
                if not refund_request.processed_by:
                    refund_request.processed_by = request.user
                    refund_request.processed_at = timezone.now()
                refund_request.stripe_refund_id = stripe_refund.id
                refund_request.save()
                print(f"DEBUG: RefundRequest status updated to '{refund_request.status}' and saved.")

                messages.success(request, f"Refund request for booking '{booking_reference_for_metadata}' has been approved and initiated with Stripe (ID: {stripe_refund.id}). Awaiting final confirmation from Stripe.")
                return redirect(admin_management_redirect_url)

        except stripe.error.StripeError as e:
            print(f"ERROR: Stripe error occurred: {e}")
            error_message = f"Stripe error initiating refund: {e.user_message or e}"
            messages.error(request, error_message)
            refund_request.status = 'failed'
            refund_request.staff_notes = (refund_request.staff_notes or "") + f"\nStripe initiation failed: {e.user_message or e} at {timezone.now()}"
            refund_request.save()
            print(f"DEBUG: RefundRequest status updated to '{refund_request.status}' due to Stripe error.")
            return redirect(admin_management_redirect_url)
        except Exception as e:
            print(f"ERROR: An unexpected error occurred: {e}")
            import traceback
            traceback.print_exc()
            error_message = f"An unexpected error occurred: {e}"
            messages.error(request, error_message)
            refund_request.status = 'failed'
            refund_request.staff_notes = (refund_request.staff_notes or "") + f"\nUnexpected error during initiation: {e} at {timezone.now()}"
            refund_request.save()
            print(f"DEBUG: RefundRequest status updated to '{refund_request.status}' due to unexpected error.")
            return redirect(admin_management_redirect_url)
