# payments/webhook_handlers/refund_handlers.py

from django.conf import settings
from decimal import Decimal

from payments.models import Payment, RefundRequest
from hire.models import HireBooking # Make sure HireBooking is imported
from service.models import ServiceBooking # Make sure ServiceBooking is imported
from mailer.utils import send_templated_email
from django.db import transaction
from django.utils import timezone
import stripe # Make sure stripe is imported

def _get_booking_from_payment(payment_obj: Payment):
    """
    Helper function to determine the booking type and retrieve the associated booking object.
    Returns (booking_obj, booking_type_str) or (None, None).
    """
    if payment_obj.hire_booking:
        return payment_obj.hire_booking, 'hire_booking'
    elif payment_obj.service_booking:
        return payment_obj.service_booking, 'service_booking'
    return None, None


def handle_booking_refunded(payment_obj: Payment, event_object_data: dict):
    """
    Handles 'charge.refunded' and 'charge.refund.updated' events.
    `event_object_data` can be either a Stripe Charge object or a Stripe Refund object.
    This function is now generic for both HireBooking and ServiceBooking.
    """
    print("DEBUG: handle_booking_refunded - Function entered.")
    print(f"DEBUG: handle_booking_refunded - payment_obj ID: {payment_obj.id}")
    print(f"DEBUG: handle_booking_refunded - event_object_data: {event_object_data}")

    try:
        with transaction.atomic():
            is_charge_object = event_object_data.get('object') == 'charge'
            is_refund_object = event_object_data.get('object') == 'refund'

            refunded_amount_decimal = Decimal('0.00')
            stripe_refund_id = None
            refund_status = None
            charge_id = None

            if is_charge_object:
                refunded_amount_cents = event_object_data.get('amount_refunded')
                if refunded_amount_cents is not None:
                    refunded_amount_decimal = Decimal(refunded_amount_cents) / Decimal('100')

                # Check for latest refund details within a charge object
                if 'refunds' in event_object_data and event_object_data['refunds'] and 'data' in event_object_data['refunds'] and event_object_data['refunds']['data']:
                    latest_refund = max(event_object_data['refunds']['data'], key=lambda r: r['created'])
                    stripe_refund_id = latest_refund.get('id')
                    refund_status = latest_refund.get('status')
                charge_id = event_object_data.get('id')

            elif is_refund_object:
                stripe_refund_id = event_object_data.get('id')
                refund_status = event_object_data.get('status')
                charge_id = event_object_data.get('charge')

                if charge_id:
                    try:
                        # Attempt to retrieve the full charge object to get total amount refunded
                        stripe.api_key = settings.STRIPE_SECRET_KEY
                        latest_charge = stripe.Charge.retrieve(charge_id)
                        if latest_charge and latest_charge.get('amount_refunded') is not None:
                            refunded_amount_decimal = Decimal(latest_charge.get('amount_refunded')) / Decimal('100')
                        else:
                            # Fallback to amount in the refund event if charge lookup fails or amount_refunded is not there
                            if event_object_data.get('amount') is not None:
                                refunded_amount_decimal = Decimal(event_object_data.get('amount')) / Decimal('100')
                    except stripe.error.StripeError as e:
                        print(f"WARNING: handle_booking_refunded - Stripe Error retrieving charge {charge_id}: {e}. Falling back to refund event amount.")
                        if event_object_data.get('amount') is not None:
                            refunded_amount_decimal = Decimal(event_object_data.get('amount')) / Decimal('100')
                else:
                    if event_object_data.get('amount') is not None:
                        refunded_amount_decimal = Decimal(event_object_data.get('amount')) / Decimal('100')

            else:
                print("DEBUG: handle_booking_refunded - Event object is neither 'charge' nor 'refund'. Exiting.")
                return # Not a refund event we need to process

            if refunded_amount_decimal <= 0:
                print(f"DEBUG: handle_booking_refunded - Refunded amount is zero or less ({refunded_amount_decimal}). No changes needed for booking/payment. Exiting.")
                return

            booking_obj, booking_type_str = _get_booking_from_payment(payment_obj)

            if not booking_obj:
                print(f"ERROR: handle_booking_refunded - No associated hire_booking or service_booking found for payment ID: {payment_obj.id}. Cannot update booking object.")
                # Continue to update Payment and RefundRequest even if booking is not found

            # --- Update Booking Object (if found) ---
            if booking_obj:
                print(f"DEBUG: handle_booking_refunded - Found {booking_type_str} object: {booking_obj}")

                # Update amount_paid for the booking
                # This logic is for the *total* refunded amount associated with the charge,
                # not just this specific refund. Stripe's `amount_refunded` on the charge
                # object is the cumulative sum.
                
                # We need to know the *original* amount paid on the booking before any refunds
                # For HireBooking, this is `payment_obj.amount` as `payment_obj` is linked to the overall transaction
                # For ServiceBooking, this is `payment_obj.amount` as well.
                
                # Set the booking's amount_paid to reflect the *remaining* amount after this refund.
                # However, the `amount_refunded` from Stripe's charge.refunded event is the total refunded *so far*.
                # So we should update payment_obj.refunded_amount first, then derive the booking's amount_paid.
                
                # For now, let's update payment_obj.refunded_amount and use that to set booking status.
                # The booking's `amount_paid` should probably mirror the `Payment` object's `amount - refunded_amount`
                booking_obj.amount_paid = payment_obj.amount - refunded_amount_decimal # Use the cumulative refunded amount from Stripe

                if booking_obj.amount_paid <= 0:
                    booking_obj.payment_status = 'refunded'
                elif booking_obj.amount_paid < payment_obj.amount:
                    booking_obj.payment_status = 'partially_refunded'
                else:
                    # If amount_paid is back to full amount (e.g., after an internal adjustment or re-charge)
                    booking_obj.payment_status = 'paid' # Or 'deposit_paid' depending on original payment method

                # Specific status updates based on booking type if needed
                if booking_type_str == 'service_booking':
                    if booking_obj.booking_status == 'declined' and booking_obj.payment_status == 'refunded':
                        booking_obj.booking_status = 'DECLINED_REFUNDED'
                elif booking_type_str == 'hire_booking':
                    if booking_obj.payment_status == 'refunded':
                        booking_obj.status = 'cancelled' # Set hire booking status to cancelled if fully refunded

                booking_obj.save()
                print(f"DEBUG: handle_booking_refunded - {booking_type_str} updated. New amount_paid: {booking_obj.amount_paid}, payment_status: {booking_obj.payment_status}, booking_status: {getattr(booking_obj, 'status', 'N/A')}")

            # --- Update Payment Object ---
            payment_obj.refunded_amount = refunded_amount_decimal # This is the cumulative refunded amount from Stripe
            if payment_obj.refunded_amount >= payment_obj.amount:
                payment_obj.status = 'refunded'
            elif payment_obj.refunded_amount > 0:
                payment_obj.status = 'partially_refunded'
            else:
                # If refunded_amount somehow became 0 (e.g., correction from Stripe)
                # This should ideally revert to the original payment status
                if payment_obj.amount == payment_obj.refunded_amount: # If it was a full refund that got corrected
                    payment_obj.status = 'succeeded' # Or original payment status like 'paid'
                else:
                    payment_obj.status = 'succeeded' # Default if no refunds are active

            payment_obj.save()
            print(f"DEBUG: handle_booking_refunded - Payment object updated. New refunded_amount: {payment_obj.refunded_amount}, status: {payment_obj.status}")

            # --- Create or Update RefundRequest ---
            # Prioritize finding an existing refund request linked to this payment and awaiting processing
            refund_request = RefundRequest.objects.filter(
                payment=payment_obj,
                status__in=['pending', 'approved', 'reviewed_pending_approval', 'partially_refunded', 'unverified']
            ).order_by('-requested_at').first() # Get the latest relevant request

            if not refund_request:
                # Create a new refund request if none exists or none is in the right status
                # Or if this refund was initiated by Stripe without a prior request from our system
                refund_request = RefundRequest.objects.create(
                    payment=payment_obj,
                    hire_booking=booking_obj if booking_type_str == 'hire_booking' else None,
                    service_booking=booking_obj if booking_type_str == 'service_booking' else None,
                    stripe_refund_id=stripe_refund_id,
                    amount_to_refund=refunded_amount_decimal, # This is the total amount refunded by Stripe
                    status='refunded' if payment_obj.status == 'refunded' else 'partially_refunded',
                    is_admin_initiated=True, # Assuming Stripe webhook initiated refund is admin-driven
                    processed_at=timezone.now(),
                    staff_notes="Refund processed automatically via Stripe webhook (initial creation)."
                )
                print(f"DEBUG: handle_booking_refunded - New RefundRequest created: {refund_request.id}")
            else:
                # Update existing refund request
                refund_request.stripe_refund_id = stripe_refund_id
                refund_request.amount_to_refund = refunded_amount_decimal # Update with total refunded from Stripe
                refund_request.status = 'refunded' if payment_obj.status == 'refunded' else 'partially_refunded'
                refund_request.processed_at = timezone.now()
                refund_request.staff_notes = (refund_request.staff_notes or "") + "\nRefund processed automatically via Stripe webhook (updated existing request)."
                refund_request.save()
                print(f"DEBUG: handle_booking_refunded - Existing RefundRequest updated: {refund_request.id}")

            # --- Send Confirmation Emails ---
            user_email = None
            booking_reference = "N/A"
            customer_name = "Customer"
            booking_for_email = None # The specific booking object to pass to the email context

            if booking_obj:
                if booking_type_str == 'hire_booking':
                    booking_reference = booking_obj.booking_reference
                    customer_name = booking_obj.driver_profile.name if booking_obj.driver_profile else "Customer"
                    user_email = booking_obj.driver_profile.user.email if booking_obj.driver_profile and booking_obj.driver_profile.user else None
                    booking_for_email = booking_obj
                elif booking_type_str == 'service_booking':
                    booking_reference = booking_obj.service_booking_reference
                    customer_name = booking_obj.service_profile.name if booking_obj.service_profile else "Customer"
                    user_email = booking_obj.service_profile.user.email if booking_obj.service_profile and booking_obj.service_profile.user else booking_obj.service_profile.email
                    booking_for_email = booking_obj

            if user_email:
                email_context = {
                    'refund_request': refund_request,
                    'refunded_amount': refunded_amount_decimal,
                    'booking_reference': booking_reference,
                    'customer_name': customer_name,
                    'admin_email': getattr(settings, 'ADMIN_EMAIL', settings.DEFAULT_FROM_EMAIL),
                    'refund_policy_link': settings.SITE_BASE_URL + '/returns/', # Assuming this URL is constant
                }
                send_templated_email(
                    recipient_list=[user_email],
                    subject=f"Your Refund for Booking {booking_reference} Has Been Processed/Updated",
                    template_name='user_refund_processed_confirmation.html', # Generic template
                    context=email_context,
                    # Pass the specific booking object to the mailer utility
                    booking=booking_for_email,
                    # Pass relevant profile if the mailer needs it for specific reasons
                    driver_profile=booking_obj.driver_profile if booking_type_str == 'hire_booking' else None,
                    service_profile=booking_obj.service_profile if booking_type_str == 'service_booking' else None,
                )
                print(f"DEBUG: handle_booking_refunded - User confirmation email sent to: {user_email}")
            else:
                print("DEBUG: handle_booking_refunded - No user email found for confirmation.")


            if settings.ADMIN_EMAIL:
                admin_email_context = {
                    'refund_request': refund_request,
                    'refunded_amount': refunded_amount_decimal,
                    'booking_reference': booking_reference,
                    'stripe_refund_id': stripe_refund_id,
                    'payment_id': payment_obj.id,
                    'payment_intent_id': payment_obj.stripe_payment_intent_id,
                    'status': refund_status,
                    'event_type': 'charge.refund.updated' if is_refund_object else 'charge.refunded',
                    'booking_type': booking_type_str,
                    'customer_name': customer_name,
                }
                send_templated_email(
                    recipient_list=[settings.ADMIN_EMAIL],
                    subject=f"Stripe Refund Processed/Updated for {booking_type_str.replace('_', ' ').title()} {booking_reference} (ID: {refund_request.pk if refund_request else 'N/A'})",
                    template_name='admin_refund_processed_notification.html', # Generic template
                    context=admin_email_context,
                    booking=booking_for_email, # Pass the specific booking object to the mailer utility
                )
                print(f"DEBUG: handle_booking_refunded - Admin notification email sent to: {settings.ADMIN_EMAIL}")
            else:
                print("DEBUG: handle_booking_refunded - ADMIN_EMAIL is not configured in settings. Skipping admin email.")

    except Exception as e:
        print(f"ERROR: handle_booking_refunded - An unexpected error occurred: {e}")
        # Re-raise the exception to ensure the transaction is rolled back
        raise


def handle_booking_refund_updated(payment_obj: Payment, event_data: dict):
    """
    Handles the 'charge.refund.updated' event for both hire_bookings and service_bookings.
    Dispatches to the handle_booking_refunded function for shared logic.
    """
    print("DEBUG: handle_booking_refund_updated - Function entered.")
    handle_booking_refunded(payment_obj, event_data)
    print("DEBUG: handle_booking_refund_updated - Function exited.")

