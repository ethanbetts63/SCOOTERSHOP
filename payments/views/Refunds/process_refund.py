import stripe
from django.shortcuts import redirect, get_object_or_404
from django.views import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.db import transaction
from django.conf import settings
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth.decorators import user_passes_test
from users.views.auth import is_admin
from payments.models import RefundRequest, Payment



@method_decorator(user_passes_test(is_admin), name='dispatch')
class ProcessHireRefundView(View):
    def post(self, request, pk, *args, **kwargs):
        hire_refund_request = get_object_or_404(RefundRequest, pk=pk)

        if hire_refund_request.status not in ['approved', 'reviewed_pending_approval']:
            messages.error(request, f"Refund request is not in an approvable state. Current status: {hire_refund_request.get_status_display()}.")
            return redirect('dashboard:admin_hire_refund_management')

        if not hire_refund_request.payment:
            messages.error(request, "Cannot process refund: No associated payment found for this request.")
            return redirect('dashboard:admin_hire_refund_management')

        if hire_refund_request.amount_to_refund is None or hire_refund_request.amount_to_refund <= 0:
            messages.error(request, "Cannot process refund: No valid amount specified to refund.")
            return redirect('dashboard:admin_hire_refund_management')

        if not hire_refund_request.payment.stripe_payment_intent_id:
            messages.error(request, "Cannot process refund: Associated payment has no Stripe Payment Intent ID.")
            return redirect('dashboard:admin_hire_refund_management')

        stripe.api_key = settings.STRIPE_SECRET_KEY 

        try:
            with transaction.atomic():
                amount_in_cents = int(hire_refund_request.amount_to_refund * Decimal('100'))

                metadata = {
                    'hire_refund_request_id': str(hire_refund_request.pk),
                    'admin_user_id': str(request.user.pk),
                    'booking_reference': hire_refund_request.hire_booking.booking_reference if hire_refund_request.hire_booking else 'N/A',
                }

                stripe_refund = stripe.Refund.create(
                    payment_intent=hire_refund_request.payment.stripe_payment_intent_id,
                    amount=amount_in_cents,
                    reason='requested_by_customer',
                    metadata=metadata
                )

                hire_refund_request.status = 'approved'
                hire_refund_request.processed_by = request.user
                hire_refund_request.processed_at = timezone.now()
                hire_refund_request.stripe_refund_id = stripe_refund.id
                hire_refund_request.save()

                messages.success(request, f"Refund for booking '{hire_refund_request.hire_booking.booking_reference}' initiated successfully with Stripe (ID: {stripe_refund.id}). Status updated to '{hire_refund_request.get_status_display()}'.")
                return redirect('dashboard:admin_hire_refund_management')

        except stripe.error.StripeError as e:
            messages.error(request, f"Stripe error initiating refund: {e.user_message or e}")
            hire_refund_request.status = 'failed'
            hire_refund_request.staff_notes = f"Stripe initiation failed: {e.user_message or e}"
            hire_refund_request.save()
            return redirect('dashboard:admin_hire_refund_management')
        except Exception as e:
            messages.error(request, f"An unexpected error occurred: {e}")
            hire_refund_request.status = 'failed'
            hire_refund_request.staff_notes = f"Unexpected error during initiation: {e}"
            hire_refund_request.save()
            return redirect('dashboard:admin_hire_refund_management')
