from django.db import transaction
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
import json
import stripe

from hire.models import HireBooking, DriverProfile
from payments.models import Payment, RefundRequest

from mailer.utils import send_templated_email


def handle_hire_booking_refunded(payment_obj: Payment, event_object_data: dict):
    """
    Handles 'charge.refunded' and 'charge.refund.updated' events.
    `event_object_data` can be either a Stripe Charge object or a Stripe Refund object.
    """

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

                if 'refunds' in event_object_data and isinstance(event_object_data['refunds'], dict) and 'data' in event_object_data['refunds'] and event_object_data['refunds']['data']:
                    latest_refund = max(event_object_data['refunds']['data'], key=lambda r: r['created'])
                    stripe_refund_id = latest_refund.get('id')
                    refund_status = latest_refund.get('status')
                elif 'refunds' in event_object_data and isinstance(event_object_data['refunds'], list) and event_object_data['refunds']:
                    latest_refund = max(event_object_data['refunds'], key=lambda r: r['created'])
                    stripe_refund_id = latest_refund.get('id')
                    refund_status = latest_refund.get('status')
                charge_id = event_object_data.get('id')

            elif is_refund_object:
                stripe_refund_id = event_object_data.get('id')
                refund_status = event_object_data.get('status')
                charge_id = event_object_data.get('charge')

                if charge_id:
                    try:
                        stripe.api_key = settings.STRIPE_SECRET_KEY
                        latest_charge = stripe.Charge.retrieve(charge_id)
                        if latest_charge and latest_charge.get('amount_refunded') is not None:
                            refunded_amount_decimal = Decimal(latest_charge.get('amount_refunded')) / Decimal('100')
                        else:
                            if event_object_data.get('amount') is not None:
                                refunded_amount_decimal = Decimal(event_object_data.get('amount')) / Decimal('100')
                    except stripe.error.StripeError as e:
                        if event_object_data.get('amount') is not None:
                            refunded_amount_decimal = Decimal(event_object_data.get('amount')) / Decimal('100')
                else:
                    if event_object_data.get('amount') is not None:
                        refunded_amount_decimal = Decimal(event_object_data.get('amount')) / Decimal('100')

            else:
                return

            if refunded_amount_decimal is None or refunded_amount_decimal <= 0:
                return

            hire_refund_request = None
            try:
                if stripe_refund_id:
                    hire_refund_request = RefundRequest.objects.filter(
                        stripe_refund_id=stripe_refund_id
                    ).first()

                if not hire_refund_request:
                    hire_refund_request = RefundRequest.objects.filter(
                        payment=payment_obj,
                        status__in=['approved', 'reviewed_pending_approval', 'pending', 'partially_refunded']
                    ).order_by('-requested_at').first()
                    if hire_refund_request:
                        if not stripe_refund_id:
                            stripe_refund_id = hire_refund_request.stripe_refund_id

            except Exception as e:
                hire_refund_request = None

            if hire_refund_request:
                # Simplified status update logic
                if refund_status == 'succeeded' and hire_refund_request.status != 'refunded':
                    # If Stripe says the refund succeeded, we mark our request as refunded.
                    # The distinction between partial/full is handled on the Payment model itself.
                    hire_refund_request.status = 'refunded'
                elif refund_status == 'failed' and hire_refund_request.status != 'failed':
                    hire_refund_request.status = 'failed'
                elif refund_status == 'pending' and hire_refund_request.status not in ['pending', 'approved', 'reviewed_pending_approval']:
                    hire_refund_request.status = 'pending'

                if stripe_refund_id and not hire_refund_request.stripe_refund_id:
                     hire_refund_request.stripe_refund_id = stripe_refund_id

                hire_refund_request.amount_to_refund = refunded_amount_decimal
                hire_refund_request.processed_at = timezone.now()
                hire_refund_request.save()
            else:
                pass


            payment_obj.refunded_amount = refunded_amount_decimal

            if payment_obj.refunded_amount >= payment_obj.amount:
                payment_obj.status = 'refunded'
            elif payment_obj.refunded_amount > 0:
                payment_obj.status = 'partially_refunded'
            else:
                if payment_obj.status == 'partially_refunded' or payment_obj.status == 'refunded':
                    payment_obj.status = 'succeeded'

            payment_obj.save()

            hire_booking = payment_obj.hire_booking
            if hire_booking:
                if payment_obj.status == 'refunded':
                    hire_booking.status = 'cancelled'
                    hire_booking.payment_status = 'refunded'
                elif payment_obj.status == 'partially_refunded':
                    hire_booking.payment_status = 'partially_refunded'
                elif payment_obj.refunded_amount == 0 and hire_booking.payment_status == 'partially_refunded':
                    hire_booking.payment_status = 'paid'
                
                hire_booking.save()
            else:
                pass

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
                    'refund_policy_link': settings.SITE_BASE_URL + '/returns/'
                }
                send_templated_email(
                    recipient_list=[user_email],
                    subject=f"Your Refund for Booking {hire_booking.booking_reference if hire_booking else 'N/A'} Has Been Processed/Updated",
                    template_name='user_refund_processed_confirmation.html',
                    context=email_context,
                    driver_profile=hire_refund_request.driver_profile if hire_refund_request else payment_obj.driver_profile,
                    booking=hire_booking
                )
            else:
                pass

            if settings.ADMIN_EMAIL:
                admin_email_context = {
                    'refund_request': hire_refund_request,
                    'refunded_amount': refunded_amount_decimal,
                    'booking_reference': hire_booking.booking_reference if hire_booking else 'N/A',
                    'stripe_refund_id': stripe_refund_id,
                    'payment_id': payment_obj.id,
                    'payment_intent_id': payment_obj.stripe_payment_intent_id,
                    'status': refund_status,
                    'event_type': 'charge.refund.updated' if is_refund_object else 'charge.refunded'
                }
                send_templated_email(
                    recipient_list=[settings.ADMIN_EMAIL],
                    subject=f"Stripe Refund Processed/Updated for Booking {hire_booking.booking_reference if hire_booking else 'N/A'} (ID: {hire_refund_request.pk if hire_refund_request else 'N/A'})",
                    template_name='admin_refund_processed_notification.html',
                    context=admin_email_context,
                    booking=hire_booking
                )

    except Exception as e:
        raise


def handle_hire_booking_refund_updated(payment_obj: Payment, event_data: dict):
    """
    Handles the 'charge.refund.updated' event for hire_bookings.
    Dispatches to the handle_hire_booking_refunded function for shared logic.
    """
    handle_hire_booking_refunded(payment_obj, event_data)
