# payments/webhook_handlers.py
from django.db import transaction
# import logging # Removed logging import
from decimal import Decimal
from django.conf import settings # Import settings to access ADMIN_EMAIL
from django.utils import timezone # Import timezone

# Import models from hire app
from hire.models import TempHireBooking, HireBooking, BookingAddOn, TempBookingAddOn
# Import Payment model from payments app
from payments.models import Payment, HireRefundRequest # Import HireRefundRequest
from hire.models import DriverProfile # Import DriverProfile

# Import the new converter function
from hire.temp_hire_converter import convert_temp_to_hire_booking

# Import the email sending utility
from mailer.utils import send_templated_email

# logger = logging.getLogger(__name__) # Removed logger initialization

def handle_hire_booking_succeeded(payment_obj: Payment, payment_intent_data: dict):
    """
    Handles the business logic for a successful payment_intent.succeeded event
    specifically for a 'hire_booking'.

    This function is responsible for:
    1. Utilizing the centralized converter to turn TempHireBooking into HireBooking.
    2. Updating the Payment object's status to reflect the successful payment.
    3. Sending confirmation emails to the user and admin.

    Args:
        payment_obj (Payment): The Payment model instance linked to this intent.
        payment_intent_data (dict): The data object from the Stripe PaymentIntent event.
    """
    print(f"DEBUG: Handling successful hire_booking payment for Payment ID: {payment_obj.id}")

    try:
        temp_booking = payment_obj.temp_hire_booking

        if temp_booking is None:
            print(f"ERROR: TempHireBooking not found for Payment ID {payment_obj.id}. Cannot finalize booking.")
            raise TempHireBooking.DoesNotExist(f"TempHireBooking for Payment ID {payment_obj.id} does not exist.")

        # Determine payment_status for the HireBooking based on the original payment option
        # Correctly map payment_option to hire_payment_status
        if temp_booking.payment_option == 'online_full':
            hire_payment_status = 'paid'
        elif temp_booking.payment_option == 'online_deposit':
            hire_payment_status = 'deposit_paid'
        elif temp_booking.payment_option == 'in_store_full': # Handle in-store payments
            hire_payment_status = 'unpaid' # Or 'in_store_unpaid' if you add that status
        else:
            # Default or error handling for unexpected payment_option
            hire_payment_status = 'unpaid' # Or raise an error
            print(f"WARNING: Unexpected payment_option '{temp_booking.payment_option}' for TempHireBooking {temp_booking.pk}. Defaulting to 'unpaid'.")


        # Use the centralized converter function
        # The converter function already handles the transaction, creation of HireBooking,
        # copying of add-ons, and deletion of TempHireBooking.
        hire_booking = convert_temp_to_hire_booking(
            temp_booking=temp_booking,
            payment_method=temp_booking.payment_option, # Payment method is online for webhook-triggered success
            booking_payment_status=hire_payment_status,
            # Use 'amount_received' from payment_intent_data for the actual amount paid by customer.
            # 'amount' is the requested amount, 'amount_received' is what was actually paid.
            amount_paid_on_booking=Decimal(payment_intent_data['amount_received']) / Decimal('100'),
            stripe_payment_intent_id=payment_obj.stripe_payment_intent_id,
            payment_obj=payment_obj, # Pass the existing payment_obj to be updated by the converter
        )

        # The payment_obj's status is updated by the converter, but we can re-confirm here
        # or add any other post-conversion logic specific to the webhook.
        # For example, ensure the payment_obj status matches the Stripe intent status.
        if payment_obj.status != payment_intent_data['status']:
            payment_obj.status = payment_intent_data['status']
            payment_obj.save()
            print(f"DEBUG: Updated Payment {payment_obj.id} status to {payment_obj.status}.")

        # --- Email Sending for Online Booking Confirmation ---
        # Context for email templates
        email_context = {
            'hire_booking': hire_booking,
            'user': hire_booking.driver_profile.user if hire_booking.driver_profile and hire_booking.driver_profile.user else None,
            'driver_profile': hire_booking.driver_profile,
            'is_in_store': False, # Flag for template logic if needed
        }

        # Send confirmation email to the user
        user_email = hire_booking.driver_profile.user.email if hire_booking.driver_profile.user else hire_booking.driver_profile.email
        if user_email:
            send_templated_email(
                recipient_list=[user_email],
                subject=f"Your Motorcycle Hire Booking Confirmation - {hire_booking.booking_reference}",
                template_name='booking_confirmation_user.html',
                context=email_context,
                user=hire_booking.driver_profile.user if hire_booking.driver_profile and hire_booking.driver_profile.user else None,
                driver_profile=hire_booking.driver_profile,
                booking=hire_booking
            )

        # Send notification email to the admin
        if settings.ADMIN_EMAIL:
            send_templated_email(
                recipient_list=[settings.ADMIN_EMAIL],
                subject=f"New Motorcycle Hire Booking (Online) - {hire_booking.booking_reference}",
                template_name='booking_confirmation_admin.html',
                context=email_context,
                booking=hire_booking
            )
        # --- End Email Sending ---

    except TempHireBooking.DoesNotExist:
        print(f"ERROR: TempHireBooking not found for Payment ID {payment_obj.id}. Cannot finalize booking.")
        # Re-raise the exception to ensure the webhook returns a 500, prompting Stripe to retry
        raise
    except Exception as e:
        print(f"CRITICAL ERROR: Critical error finalizing hire booking for Payment ID {payment_obj.id}: {e}")
        # Re-raise the exception to ensure the webhook returns a 500, prompting Stripe to retry
        raise


def handle_hire_booking_refunded(payment_obj: Payment, event_data: dict):
    """
    Handles the business logic for a successful 'charge.refunded' event
    specifically for a 'hire_booking'.

    This function is responsible for:
    1. Extracting refund details from the Stripe event.
    2. Finding and updating the associated HireRefundRequest.
    3. Updating the Payment object's status and refunded_amount.
    4. Updating the HireBooking's payment_status and overall status (e.g., to cancelled).
    5. Sending confirmation emails to the user and admin.

    Args:
        payment_obj (Payment): The Payment model instance linked to this intent.
                               (Note: This payment_obj is found by the webhook_view
                                      using the payment_intent_id from the event).
        event_data (dict): The data object from the Stripe 'charge.refunded' event.
    """
    print(f"DEBUG: Handling 'charge.refunded' event for Payment ID: {payment_obj.id}")

    try:
        with transaction.atomic():  # Ensure database consistency for all updates

            # Extract refund data from the event payload
            # The 'charge.refunded' event's 'data.object' is a Charge object,
            # which contains a 'refunds' array if there are multiple refunds,
            # or the primary refund details if it's a single refund.
            # For simplicity, we'll assume the event refers to the most recent refund
            # or the primary refund on the charge.
            # Stripe's 'charge.refunded' event data object is the Charge itself,
            # which contains the 'refunds' array.
            charge_object = event_data # This is the Charge object from the webhook payload
            refunds_list = charge_object.get('refunds', {}).get('data', [])

            if not refunds_list:
                print(f"WARNING: No refund data found in 'charge.refunded' event for Payment ID: {payment_obj.id}")
                return # Nothing to process if no refund data

            # Get the most recent refund object from the list
            # The refunds list is typically ordered by creation time, so the last one is most recent.
            # Or, you might want to iterate if handling multiple refunds in one go (less common for this event).
            # For 'charge.refunded', typically one refund is being reported.
            stripe_refund_data = refunds_list[0] # Assuming the first (or only) refund in the list

            stripe_refund_id = stripe_refund_data['id']
            refunded_amount_cents = stripe_refund_data['amount'] # Amount in cents
            refunded_amount_decimal = Decimal(refunded_amount_cents) / Decimal('100')
            refund_reason = stripe_refund_data.get('reason')
            refund_status = stripe_refund_data.get('status') # e.g., 'succeeded', 'pending', 'failed'

            print(f"DEBUG: Stripe Refund ID: {stripe_refund_id}, Amount: {refunded_amount_decimal}, Status: {refund_status}")

            # 1. Find the associated HireRefundRequest
            # We assume there's a HireRefundRequest linked to this payment intent
            # that initiated this refund.
            try:
                # Find the HireRefundRequest that is linked to this payment
                # and is in an 'approved' or 'reviewed_pending_approval' state,
                # or has no stripe_refund_id yet.
                # Prioritize finding a request that matches the expected state.
                # If multiple, pick the most recent one that's not yet 'refunded'.
                hire_refund_request = HireRefundRequest.objects.filter(
                    payment=payment_obj,
                    status__in=['approved', 'reviewed_pending_approval', 'pending'] # Target states before 'refunded'
                ).order_by('-requested_at').first()

                if not hire_refund_request:
                    # Fallback: try to find by stripe_refund_id if already set (e.g., retry)
                    hire_refund_request = HireRefundRequest.objects.filter(
                        stripe_refund_id=stripe_refund_id
                    ).first()
                    if not hire_refund_request:
                        print(f"WARNING: No matching HireRefundRequest found for Payment {payment_obj.id} and Stripe Refund ID {stripe_refund_id}. This refund might be external or already processed.")
                        # If no matching request is found, we can't update our internal request.
                        # However, we still need to update the Payment and Booking.
                        pass # Continue to update Payment and HireBooking

            except HireRefundRequest.DoesNotExist:
                print(f"WARNING: No HireRefundRequest found for Payment {payment_obj.id}. This refund might be external.")
                hire_refund_request = None # Ensure it's None if not found

            # 2. Update HireRefundRequest (if found)
            if hire_refund_request:
                if refund_status == 'succeeded':
                    hire_refund_request.status = 'refunded'
                elif refund_status == 'failed':
                    hire_refund_request.status = 'failed'
                # You can add more status mappings if Stripe provides them
                hire_refund_request.stripe_refund_id = stripe_refund_id
                hire_refund_request.amount_to_refund = refunded_amount_decimal # Update with actual refunded amount
                hire_refund_request.processed_at = timezone.now() # Mark as processed by the system
                # processed_by might remain null or be set to a system user if desired
                hire_refund_request.save()
                print(f"DEBUG: Updated HireRefundRequest {hire_refund_request.id} to status '{hire_refund_request.status}'.")
            else:
                print(f"DEBUG: No HireRefundRequest to update for Payment {payment_obj.id}. Proceeding with Payment and Booking updates.")


            # 3. Update the Payment object
            # Add the refunded amount to the existing refunded_amount (for partial refunds)
            payment_obj.refunded_amount = (payment_obj.refunded_amount or Decimal('0.00')) + refunded_amount_decimal

            # Update the payment status. If the refunded amount equals the original amount, it's fully refunded.
            if payment_obj.refunded_amount >= payment_obj.amount:
                payment_obj.status = 'refunded'
            else:
                payment_obj.status = 'partially_refunded' # You might need to add this status to your Payment model choices

            payment_obj.save()
            print(f"DEBUG: Updated Payment {payment_obj.id} status to '{payment_obj.status}' and refunded_amount to {payment_obj.refunded_amount}.")

            # 4. Update the associated HireBooking
            hire_booking = payment_obj.hire_booking
            if hire_booking:
                # If the entire booking amount is refunded, mark the booking as cancelled
                if payment_obj.status == 'refunded': # Check payment_obj's status after update
                    hire_booking.status = 'cancelled'
                    hire_booking.payment_status = 'refunded'
                elif payment_obj.status == 'partially_refunded':
                    # For partial refunds, the booking might remain 'confirmed' or go to a 'partially_refunded' status
                    # depending on your business logic. For now, we'll keep it as is unless fully refunded.
                    hire_booking.payment_status = 'partially_refunded' # You might need to add this status
                hire_booking.save()
                print(f"DEBUG: Updated HireBooking {hire_booking.id} status to '{hire_booking.status}' and payment_status to '{hire_booking.payment_status}'.")

            # 5. Send confirmation email to the user (if a request was found)
            if hire_refund_request:
                user_email = hire_refund_request.request_email
                if not user_email and hire_refund_request.driver_profile and hire_refund_request.driver_profile.user:
                    user_email = hire_refund_request.driver_profile.user.email

                if user_email:
                    email_context = {
                        'refund_request': hire_refund_request,
                        'refunded_amount': refunded_amount_decimal,
                        'booking_reference': hire_booking.booking_reference if hire_booking else 'N/A',
                        'admin_email': getattr(settings, 'ADMIN_EMAIL', settings.DEFAULT_FROM_EMAIL),
                        'refund_policy_link': settings.SITE_BASE_URL + '/returns/' # Adjust as per your actual URL
                    }
                    send_templated_email(
                        recipient_list=[user_email],
                        subject=f"Your Refund for Booking {hire_booking.booking_reference if hire_booking else 'N/A'} Has Been Processed",
                        template_name='user_refund_processed_confirmation.html', # New template for processed refund
                        context=email_context,
                        driver_profile=hire_refund_request.driver_profile,
                        booking=hire_booking
                    )
                    print(f"DEBUG: Sent refund processed confirmation email to {user_email}.")
                else:
                    print(f"WARNING: Could not send refund processed email for HireRefundRequest {hire_refund_request.id}: no recipient email found.")

            # 6. Send notification email to the admin
            if settings.ADMIN_EMAIL:
                admin_email_context = {
                    'refund_request': hire_refund_request,
                    'refunded_amount': refunded_amount_decimal,
                    'booking_reference': hire_booking.booking_reference if hire_booking else 'N/A',
                    'stripe_refund_id': stripe_refund_id,
                    'payment_id': payment_obj.id,
                    'payment_intent_id': payment_obj.stripe_payment_intent_id,
                    'status': refund_status,
                }
                send_templated_email(
                    recipient_list=[settings.ADMIN_EMAIL],
                    subject=f"Stripe Refund Processed for Booking {hire_booking.booking_reference if hire_booking else 'N/A'} (ID: {hire_refund_request.pk if hire_refund_request else 'N/A'})",
                    template_name='admin_refund_processed_notification.html', # New template for admin notification
                    context=admin_email_context,
                    booking=hire_booking
                )
                print(f"DEBUG: Sent admin refund processed notification email.")

    except Exception as e:
        print(f"CRITICAL ERROR: Critical error processing 'charge.refunded' webhook for Payment ID {payment_obj.id}: {e}")
        # Re-raise the exception to ensure the webhook returns a 500, prompting Stripe to retry
        raise


# You can define a dictionary to map booking_type to handler functions
WEBHOOK_HANDLERS = {
    'hire_booking': {
        'payment_intent.succeeded': handle_hire_booking_succeeded,
        'charge.refunded': handle_hire_booking_refunded, # Added the new refund handler
    },
    # 'service_booking': {
    #     'payment_intent.succeeded': handle_service_booking_succeeded,
    # },
    # Add more booking types and their handlers here
}
