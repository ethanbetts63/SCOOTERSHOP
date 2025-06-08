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
class ProcessRefundView(View): # Renamed class to be generic
    """
    Handles the processing of refund requests, initiating Stripe refunds.
    This view is generalized to process refunds for both HireBookings and ServiceBookings.
    """
    def post(self, request, pk, *args, **kwargs):
        refund_request = get_object_or_404(RefundRequest, pk=pk)

        # Determine the redirect URL for admin management based on booking type
        # This assumes separate admin views for hire and service refund management
        admin_management_redirect_url = 'dashboard:admin_refund_management_list' # Generic fallback
        if refund_request.hire_booking:
            admin_management_redirect_url = 'dashboard:admin_hire_refund_management'
        elif refund_request.service_booking:
            admin_management_redirect_url = 'dashboard:admin_service_refund_management' # Assuming this exists

        # Basic validation checks
        if refund_request.status not in ['approved', 'reviewed_pending_approval']:
            messages.error(request, f"Refund request is not in an approvable state. Current status: {refund_request.get_status_display()}.")
            return redirect(admin_management_redirect_url)

        if not refund_request.payment:
            messages.error(request, "Cannot process refund: No associated payment found for this request.")
            return redirect(admin_management_redirect_url)

        if refund_request.amount_to_refund is None or refund_request.amount_to_refund <= 0:
            messages.error(request, "Cannot process refund: No valid amount specified to refund.")
            return redirect(admin_management_redirect_url)

        if not refund_request.payment.stripe_payment_intent_id:
            messages.error(request, "Cannot process refund: Associated payment has no Stripe Payment Intent ID.")
            return redirect(admin_management_redirect_url)

        # Set Stripe API key from Django settings
        stripe.api_key = settings.STRIPE_SECRET_KEY

        try:
            with transaction.atomic():
                amount_in_cents = int(refund_request.amount_to_refund * Decimal('100'))

                # Dynamically set metadata based on booking type
                booking_reference_for_metadata = "N/A"
                if refund_request.hire_booking:
                    booking_reference_for_metadata = refund_request.hire_booking.booking_reference
                elif refund_request.service_booking:
                    booking_reference_for_metadata = refund_request.service_booking.service_booking_reference

                metadata = {
                    'refund_request_id': str(refund_request.pk), # Generic ID
                    'admin_user_id': str(request.user.pk),
                    'booking_reference': booking_reference_for_metadata,
                    'booking_type': 'hire' if refund_request.hire_booking else 'service' if refund_request.service_booking else 'unknown',
                }

                # Create the Stripe refund
                stripe_refund = stripe.Refund.create(
                    payment_intent=refund_request.payment.stripe_payment_intent_id,
                    amount=amount_in_cents,
                    reason='requested_by_customer',
                    metadata=metadata
                )

                # Update RefundRequest status and details
                refund_request.status = 'refunded' # Changed from 'approved' to 'refunded' directly after Stripe success
                refund_request.processed_by = request.user
                refund_request.processed_at = timezone.now()
                refund_request.stripe_refund_id = stripe_refund.id
                refund_request.save()

                messages.success(request, f"Refund for booking '{booking_reference_for_metadata}' initiated successfully with Stripe (ID: {stripe_refund.id}). Status updated to '{refund_request.get_status_display()}'.")
                return redirect(admin_management_redirect_url)

        except stripe.error.StripeError as e:
            messages.error(request, f"Stripe error initiating refund: {e.user_message or e}")
            refund_request.status = 'failed'
            refund_request.staff_notes = f"Stripe initiation failed: {e.user_message or e}"
            refund_request.save()
            return redirect(admin_management_redirect_url)
        except Exception as e:
            messages.error(request, f"An unexpected error occurred: {e}")
            refund_request.status = 'failed'
            refund_request.staff_notes = f"Unexpected error during initiation: {e}"
            refund_request.save()
            return redirect(admin_management_redirect_url)

