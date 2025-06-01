# payments/webhook_handlers.py
from django.db import transaction
from decimal import Decimal
from django.conf import settings # Import settings to access ADMIN_EMAIL
from django.utils import timezone # Import timezone
import json # <--- ADDED THIS IMPORT

# Import models from hire app
from hire.models import TempHireBooking, HireBooking, BookingAddOn, TempBookingAddOn
# Import Payment model from payments app
from payments.models import Payment, HireRefundRequest # Import HireRefundRequest
from hire.models import DriverProfile # Import DriverProfile

# Import the new converter function
from hire.temp_hire_converter import convert_temp_to_hire_booking

# Import the email sending utility
from mailer.utils import send_templated_email


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
    print(f"DEBUG: Entering handle_hire_booking_succeeded for Payment ID: {payment_obj.id}")

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
            print(f"DEBUG: Sent user booking confirmation email to {user_email}.") # Debug print

        # Send notification email to the admin
        if settings.ADMIN_EMAIL:
            send_templated_email(
                recipient_list=[settings.ADMIN_EMAIL],
                subject=f"New Motorcycle Hire Booking (Online) - {hire_booking.booking_reference}",
                template_name='booking_confirmation_admin.html',
                context=email_context,
                booking=hire_booking
            )
            print(f"DEBUG: Sent admin booking confirmation email.") # Debug print
        # --- End Email Sending ---

    except TempHireBooking.DoesNotExist:
        print(f"ERROR: TempHireBooking not found for Payment ID {payment_obj.id} in handle_hire_booking_succeeded. Cannot finalize booking.")
        # Re-raise the exception to ensure the webhook returns a 500, prompting Stripe to retry
        raise
    except Exception as e:
        print(f"CRITICAL ERROR: Critical error finalizing hire booking for Payment ID {payment_obj.id} in handle_hire_booking_succeeded: {e}")
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
    print(f"DEBUG: Entering handle_hire_booking_refunded for Payment ID: {payment_obj.id}")
    print(f"DEBUG: Received event_data: {json.dumps(event_data, indent=2)}") # Print full event data for inspection

    try:
        with transaction.atomic():  # Ensure database consistency for all updates

            # Extract refund data from the event payload
            charge_object = event_data # This is the Charge object from the webhook payload
            refunds_list = charge_object.get('refunds', {}).get('data', [])

            if not refunds_list:
                print(f"WARNING: No refund data found in 'charge.refunded' event for Payment ID: {payment_obj.id}. Exiting handler.")
                return # Nothing to process if no refund data

            stripe_refund_data = refunds_list[0] # Assuming the first (or only) refund in the list

            stripe_refund_id = stripe_refund_data['id']
            refunded_amount_cents = stripe_refund_data['amount'] # Amount in cents
            refunded_amount_decimal = Decimal(refunded_amount_cents) / Decimal('100')
            refund_reason = stripe_refund_data.get('reason')
            refund_status = stripe_refund_data.get('status') # e.g., 'succeeded', 'pending', 'failed'

            print(f"DEBUG: Extracted Stripe Refund ID: {stripe_refund_id}, Amount: {refunded_amount_decimal}, Status: {refund_status}")

            # 1. Find the associated HireRefundRequest
            hire_refund_request = None
            try:
                # Try to find a request that is linked to this payment and is awaiting processing
                hire_refund_request = HireRefundRequest.objects.filter(
                    payment=payment_obj,
                    status__in=['approved', 'reviewed_pending_approval', 'pending']
                ).order_by('-requested_at').first()

                if not hire_refund_request:
                    # If not found by status, try to find by stripe_refund_id (for retries or external refunds)
                    hire_refund_request = HireRefundRequest.objects.filter(
                        stripe_refund_id=stripe_refund_id
                    ).first()

                if hire_refund_request:
                    print(f"DEBUG: Found HireRefundRequest: {hire_refund_request.id} with current status: {hire_refund_request.status}")
                else:
                    print(f"WARNING: No matching HireRefundRequest found for Payment {payment_obj.id} and Stripe Refund ID {stripe_refund_id}. This refund might be external or already processed. Will proceed to update Payment and Booking if possible.")

            except Exception as e:
                print(f"ERROR: Error finding HireRefundRequest for Payment {payment_obj.id}: {e}")
                hire_refund_request = None # Ensure it's None if an error occurred during lookup

            # 2. Update HireRefundRequest (if found)
            if hire_refund_request:
                if refund_status == 'succeeded':
                    hire_refund_request.status = 'refunded'
                elif refund_status == 'failed':
                    hire_refund_request.status = 'failed'
                # Add more status mappings if Stripe provides them
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
                # Ensure 'partially_refunded' is a valid choice in your Payment model's status field
                payment_obj.status = 'partially_refunded'
                print("WARNING: 'partially_refunded' status used. Ensure this is a valid choice in your Payment model.")

            payment_obj.save()
            print(f"DEBUG: Updated Payment {payment_obj.id} status to '{payment_obj.status}' and refunded_amount to {payment_obj.refunded_amount}.")

            # 4. Update the associated HireBooking
            hire_booking = payment_obj.hire_booking
            if hire_booking:
                print(f"DEBUG: Found associated HireBooking: {hire_booking.id} (current status: {hire_booking.status}, payment_status: {hire_booking.payment_status})")
                # If the entire booking amount is refunded, mark the booking as cancelled
                if payment_obj.status == 'refunded': # Check payment_obj's status after update
                    hire_booking.status = 'cancelled'
                    hire_booking.payment_status = 'refunded'
                    print(f"DEBUG: HireBooking {hire_booking.id} fully refunded. Setting status to 'cancelled' and payment_status to 'refunded'.")
                elif payment_obj.status == 'partially_refunded':
                    hire_booking.payment_status = 'partially_refunded' # Ensure this is a valid status
                    print(f"DEBUG: HireBooking {hire_booking.id} partially refunded. Setting payment_status to 'partially_refunded'.")
                hire_booking.save()
                print(f"DEBUG: Updated HireBooking {hire_booking.id} status to '{hire_booking.status}' and payment_status to '{hire_booking.payment_status}'.")
            else:
                print(f"WARNING: No HireBooking associated with Payment {payment_obj.id}. Cannot update booking status.")

            # 5. Send confirmation email to the user (if a request was found or email is available)
            user_email = None
            if hire_refund_request and hire_refund_request.request_email:
                user_email = hire_refund_request.request_email
            elif hire_refund_request and hire_refund_request.driver_profile and hire_refund_request.driver_profile.user:
                user_email = hire_refund_request.driver_profile.user.email
            elif payment_obj.driver_profile and payment_obj.driver_profile.user:
                user_email = payment_obj.driver_profile.user.email

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
                    driver_profile=hire_refund_request.driver_profile if hire_refund_request else payment_obj.driver_profile,
                    booking=hire_booking
                )
                print(f"DEBUG: Sent refund processed confirmation email to {user_email}.")
            else:
                print(f"WARNING: Could not send user refund processed email for Payment {payment_obj.id}: no recipient email found.")

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
