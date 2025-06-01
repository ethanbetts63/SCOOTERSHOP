# payments/views/HireRefunds/process_refund_view.py
import stripe
from django.shortcuts import redirect, get_object_or_404
from django.views import View
from django.contrib.auth.decorators import login_required, staff_member_required
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.db import transaction
from django.conf import settings
from decimal import Decimal

from payments.models import HireRefundRequest, Payment # Import Payment model
from mailer.utils import send_templated_email # Assuming you have this

@method_decorator(login_required, name='dispatch')
@method_decorator(staff_member_required, name='dispatch')
class ProcessHireRefundView(View):
    def post(self, request, pk, *args, **kwargs):
        # 1. Get the HireRefundRequest instance
        hire_refund_request = get_object_or_404(HireRefundRequest, pk=pk)

        # Basic validation: Only process if status is 'approved' or 'reviewed_pending_approval'
        if hire_refund_request.status not in ['approved', 'reviewed_pending_approval']:
            messages.error(request, f"Refund request is not in an approvable state. Current status: {hire_refund_request.get_status_display()}")
            return redirect('dashboard:admin_hire_refund_management') # Redirect back to management page

        # Ensure there's a linked payment and an amount to refund
        if not hire_refund_request.payment:
            messages.error(request, "Cannot process refund: No associated payment found for this request.")
            return redirect('dashboard:admin_hire_refund_management')

        if not hire_refund_request.amount_to_refund:
            messages.error(request, "Cannot process refund: No amount specified to refund.")
            return redirect('dashboard:admin_hire_refund_management')

        # Ensure the payment has a Stripe Payment Intent ID
        if not hire_refund_request.payment.stripe_payment_intent_id:
            messages.error(request, "Cannot process refund: Associated payment has no Stripe Payment Intent ID.")
            return redirect('dashboard:admin_hire_refund_management')

        # Set your Stripe API key
        stripe.api_key = settings.STRIPE_SECRET_KEY # Make sure this is correctly set in your settings.py

        try:
            with transaction.atomic():
                # Convert amount to cents for Stripe API
                amount_in_cents = int(hire_refund_request.amount_to_refund * Decimal('100'))

                # Prepare metadata for Stripe refund
                metadata = {
                    'hire_refund_request_id': str(hire_refund_request.pk),
                    'admin_user_id': str(request.user.pk),
                    'booking_reference': hire_refund_request.hire_booking.booking_reference if hire_refund_request.hire_booking else 'N/A',
                }

                # Call Stripe API to create the refund
                print(f"DEBUG: Attempting to create Stripe refund for Payment Intent {hire_refund_request.payment.stripe_payment_intent_id} with amount {amount_in_cents} cents.")
                stripe_refund = stripe.Refund.create(
                    payment_intent=hire_refund_request.payment.stripe_payment_intent_id,
                    amount=amount_in_cents,
                    reason='requested_by_customer', # Or use hire_refund_request.reason if applicable
                    metadata=metadata
                )
                print(f"DEBUG: Stripe Refund initiated: {stripe_refund.id}")

                # Update the HireRefundRequest status immediately to reflect initiation
                # The webhook will handle the final 'refunded' status.
                hire_refund_request.status = 'approved' # Or 'approved_awaiting_stripe' if you add that status
                hire_refund_request.processed_by = request.user
                hire_refund_request.processed_at = timezone.now()
                hire_refund_request.save()

                messages.success(request, f"Refund for booking '{hire_refund_request.hire_booking.booking_reference}' initiated successfully with Stripe (ID: {stripe_refund.id}). Status updated to '{hire_refund_request.get_status_display()}'.")
                return redirect('dashboard:admin_hire_refund_management')

        except stripe.error.StripeError as e:
            # Catch Stripe-specific errors
            messages.error(request, f"Stripe error initiating refund: {e.user_message or e}")
            print(f"ERROR: Stripe error during refund initiation: {e}")
            # Optionally, update refund request status to 'failed' here
            hire_refund_request.status = 'failed'
            hire_refund_request.staff_notes = f"Stripe initiation failed: {e.user_message or e}"
            hire_refund_request.save()
            return redirect('dashboard:admin_hire_refund_management')
        except Exception as e:
            # Catch any other unexpected errors
            messages.error(request, f"An unexpected error occurred: {e}")
            print(f"CRITICAL ERROR: Unexpected error during refund initiation: {e}")
            # Optionally, update refund request status to 'failed' here
            hire_refund_request.status = 'failed'
            hire_refund_request.staff_notes = f"Unexpected error during initiation: {e}"
            hire_refund_request.save()
            return redirect('dashboard:admin_hire_refund_management')