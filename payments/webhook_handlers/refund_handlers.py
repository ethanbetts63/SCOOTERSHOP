# payments/webhook_handlers/refund_handlers.py
from django.db import transaction
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
import json
import stripe # Import stripe library to retrieve charge object

# Import models from hire app needed for refund context (e.g., HireBooking, DriverProfile)
from hire.models import HireBooking, DriverProfile
# Import Payment and HireRefundRequest models from payments app
from payments.models import Payment, HireRefundRequest

# Import the email sending utility
from mailer.utils import send_templated_email


def handle_hire_booking_refunded(payment_obj: Payment, event_object_data: dict):
    """
    Handles 'charge.refunded' and 'charge.refund.updated' events.
    `event_object_data` can be either a Stripe Charge object or a Stripe Refund object.
    """
    print(f"DEBUG: Entering handle_hire_booking_refunded for Payment ID: {payment_obj.id}")
    print(f"DEBUG: Received event_object_data: {json.dumps(event_object_data, indent=2)}")

    try:
        with transaction.atomic():  # Ensure database consistency for all updates

            # Determine if the event_object_data is a Charge or a Refund object
            is_charge_object = event_object_data.get('object') == 'charge'
            is_refund_object = event_object_data.get('object') == 'refund'

            refunded_amount_decimal = Decimal('0.00')
            stripe_refund_id = None
            refund_status = None
            charge_id = None # To link back to the charge if we receive a refund object

            if is_charge_object:
                # This is a charge object (e.g., from charge.refunded)
                refunded_amount_cents = event_object_data.get('amount_refunded')
                if refunded_amount_cents is not None:
                    refunded_amount_decimal = Decimal(refunded_amount_cents) / Decimal('100')

                # Try to get the latest refund object from the charge's refunds array
                if 'refunds' in event_object_data and isinstance(event_object_data['refunds'], dict) and 'data' in event_object_data['refunds'] and event_object_data['refunds']['data']:
                    latest_refund = max(event_object_data['refunds']['data'], key=lambda r: r['created'])
                    stripe_refund_id = latest_refund.get('id')
                    refund_status = latest_refund.get('status')
                elif 'refunds' in event_object_data and isinstance(event_object_data['refunds'], list) and event_object_data['refunds']:
                    latest_refund = max(event_object_data['refunds'], key=lambda r: r['created'])
                    stripe_refund_id = latest_refund.get('id')
                    refund_status = latest_refund.get('status')
                else:
                    print(f"WARNING: Could not find explicit Stripe Refund ID or status in charge object's 'refunds' array for Payment ID {payment_obj.id}.")
                charge_id = event_object_data.get('id') # This is the charge ID

            elif is_refund_object:
                # This is a refund object (e.g., from charge.refund.updated)
                stripe_refund_id = event_object_data.get('id')
                refund_status = event_object_data.get('status')
                charge_id = event_object_data.get('charge') # Get the charge ID associated with this refund

                if charge_id:
                    try:
                        stripe.api_key = settings.STRIPE_SECRET_KEY # Ensure API key is set
                        latest_charge = stripe.Charge.retrieve(charge_id)
                        if latest_charge and latest_charge.get('amount_refunded') is not None:
                            refunded_amount_decimal = Decimal(latest_charge.get('amount_refunded')) / Decimal('100')
                            print(f"DEBUG: Fetched total amount_refunded from charge {charge_id}: {refunded_amount_decimal}")
                        else:
                            print(f"WARNING: Could not retrieve total amount_refunded from charge {charge_id}. Falling back to individual refund amount.")
                            # Fallback to the individual refund amount if total is not found
                            if event_object_data.get('amount') is not None:
                                refunded_amount_decimal = Decimal(event_object_data.get('amount')) / Decimal('100')
                    except stripe.error.StripeError as e:
                        print(f"ERROR: Could not retrieve charge {charge_id} for refund update: {e}. Falling back to individual refund amount.")
                        # Fallback to the individual refund amount if fetching charge fails
                        if event_object_data.get('amount') is not None:
                            refunded_amount_decimal = Decimal(event_object_data.get('amount')) / Decimal('100')
                else:
                    print(f"WARNING: No charge ID found in refund object for Payment ID {payment_obj.id}. Falling back to individual refund amount.")
                    # Fallback to the individual refund amount if no charge ID
                    if event_object_data.get('amount') is not None:
                        refunded_amount_decimal = Decimal(event_object_data.get('amount')) / Decimal('100')

            else:
                print(f"WARNING: Unknown object type in event_object_data: {event_object_data.get('object')}. Exiting handler.")
                return # Cannot process unknown object type

            # Now, check if we actually got a valid refunded_amount_decimal before proceeding
            # This check is now after the logic for determining refunded_amount_decimal based on object type
            if refunded_amount_decimal is None or refunded_amount_decimal <= 0:
                print(f"WARNING: Deduced refunded_amount_decimal is invalid ({refunded_amount_decimal}) for Payment ID: {payment_obj.id}. Exiting handler.")
                return # Nothing to process if no valid refund amount

            print(f"DEBUG: Processed Refund Amount: {refunded_amount_decimal}, Deduced Status: {refund_status}, Stripe Refund ID: {stripe_refund_id}")

            # 1. Find the associated HireRefundRequest
            hire_refund_request = None
            try:
                # Prioritize finding by the stripe_refund_id if we have it
                if stripe_refund_id:
                    hire_refund_request = HireRefundRequest.objects.filter(
                        stripe_refund_id=stripe_refund_id
                    ).first()
                    if hire_refund_request:
                        print(f"DEBUG: Found HireRefundRequest by stripe_refund_id: {hire_refund_request.id}")

                # If not found by stripe_refund_id, or if stripe_refund_id was not available from event,
                # try to find by payment_obj and expected statuses.
                if not hire_refund_request:
                    hire_refund_request = HireRefundRequest.objects.filter(
                        payment=payment_obj,
                        status__in=['approved', 'reviewed_pending_approval', 'pending', 'partially_refunded'] # Include partially_refunded for updates
                    ).order_by('-requested_at').first()
                    if hire_refund_request:
                        print(f"DEBUG: Found HireRefundRequest by payment_obj and status: {hire_refund_request.id}")
                        # If found this way, and we didn't get stripe_refund_id from event,
                        # use the one already saved on the request (from ProcessHireRefundView)
                        if not stripe_refund_id:
                            stripe_refund_id = hire_refund_request.stripe_refund_id
                            print(f"DEBUG: Using stripe_refund_id from HireRefundRequest: {stripe_refund_id}")


                if hire_refund_request:
                    print(f"DEBUG: Final HireRefundRequest found: {hire_refund_request.id} with current status: {hire_refund_request.status}")
                else:
                    print(f"WARNING: No matching HireRefundRequest found for Payment {payment_obj.id}. This refund might be external or already processed. Will proceed to update Payment and Booking if possible.")

            except Exception as e:
                print(f"ERROR: Error finding HireRefundRequest for Payment {payment_obj.id}: {e}")
                hire_refund_request = None # Ensure it's None if an error occurred during lookup

            # 2. Update HireRefundRequest (if found)
            if hire_refund_request:
                # Only update status if the incoming refund status is 'succeeded' or 'failed'
                # and it's a more definitive state than the current one.
                if refund_status == 'succeeded' and hire_refund_request.status not in ['refunded', 'partially_refunded']:
                    # If the total refunded amount equals the request amount, mark as refunded
                    if refunded_amount_decimal >= hire_refund_request.amount_to_refund: # Use the total refunded amount here
                        hire_refund_request.status = 'refunded'
                    else:
                        hire_refund_request.status = 'partially_refunded'
                elif refund_status == 'failed' and hire_refund_request.status != 'failed':
                    hire_refund_request.status = 'failed'
                elif refund_status == 'pending' and hire_refund_request.status not in ['pending', 'approved', 'reviewed_pending_approval']:
                    hire_refund_request.status = 'pending' # Or a specific 'stripe_pending' if you add it

                if stripe_refund_id and not hire_refund_request.stripe_refund_id:
                     hire_refund_request.stripe_refund_id = stripe_refund_id # Ensure ID is saved if found later

                # Always update the amount_to_refund with the latest actual refunded amount from Stripe
                hire_refund_request.amount_to_refund = refunded_amount_decimal # Update with actual total refunded amount
                hire_refund_request.processed_at = timezone.now() # Mark as processed by the system
                hire_refund_request.save()
                print(f"DEBUG: Updated HireRefundRequest {hire_refund_request.id} to status '{hire_refund_request.status}'.")
            else:
                print(f"DEBUG: No HireRefundRequest to update for Payment {payment_obj.id}. Proceeding with Payment and Booking updates.")


            # 3. Update the Payment object
            # Always set refunded_amount to the total amount_refunded from the charge object
            payment_obj.refunded_amount = refunded_amount_decimal

            # Update the payment status based on the total refunded amount vs original amount
            if payment_obj.refunded_amount >= payment_obj.amount:
                payment_obj.status = 'refunded'
            elif payment_obj.refunded_amount > 0: # If some amount is refunded but not all
                # Ensure 'partially_refunded' is a valid choice in your Payment model's status field
                payment_obj.status = 'partially_refunded'
                print("WARNING: 'partially_refunded' status used. Ensure this is a valid choice in your Payment model's status field.")
            else:
                # If refunded_amount is 0, keep original status or reset if it was 'partially_refunded'
                # This case might happen if a refund was attempted and then reversed to 0
                if payment_obj.status == 'partially_refunded' or payment_obj.status == 'refunded':
                    payment_obj.status = 'succeeded' # Or whatever the original successful status was
                    print(f"DEBUG: Payment {payment_obj.id} refunded amount is 0, resetting status to 'succeeded'.")

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
                # If a partial refund was reversed, and refunded_amount is now 0, reset payment_status
                elif payment_obj.refunded_amount == 0 and hire_booking.payment_status == 'partially_refunded':
                    hire_booking.payment_status = 'paid' # Assuming it was originally 'paid'
                    print(f"DEBUG: HireBooking {hire_booking.id} partial refund reversed. Setting payment_status back to 'paid'.")
                
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
                    subject=f"Your Refund for Booking {hire_booking.booking_reference if hire_booking else 'N/A'} Has Been Processed/Updated",
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
                    'status': refund_status, # Use the refund object's status if available
                    'event_type': 'charge.refund.updated' if is_refund_object else 'charge.refunded' # Indicate which event triggered this
                }
                send_templated_email(
                    recipient_list=[settings.ADMIN_EMAIL],
                    subject=f"Stripe Refund Processed/Updated for Booking {hire_booking.booking_reference if hire_booking else 'N/A'} (ID: {hire_refund_request.pk if hire_refund_request else 'N/A'})",
                    template_name='admin_refund_processed_notification.html', # New template for admin notification
                    context=admin_email_context,
                    booking=hire_booking
                )
                print(f"DEBUG: Sent admin refund processed notification email.")

    except Exception as e:
        print(f"CRITICAL ERROR: Critical error processing 'charge.refunded' or 'charge.refund.updated' webhook for Payment ID {payment_obj.id}: {e}")
        # Re-raise the exception to ensure the webhook returns a 500, prompting Stripe to retry
        raise


def handle_hire_booking_refund_updated(payment_obj: Payment, event_data: dict):
    """
    Handles the 'charge.refund.updated' event for hire_bookings.
    Dispatches to the handle_hire_booking_refunded function for shared logic.
    """
    print(f"DEBUG: Entering handle_hire_booking_refund_updated for Payment ID: {payment_obj.id}")
    # Call the existing refund handler, as the logic for updating models is largely the same
    handle_hire_booking_refunded(payment_obj, event_data)

