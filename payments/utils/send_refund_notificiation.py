# payments/utils/notification_sender.py

from django.conf import settings
from mailer.utils import send_templated_email
from payments.models import Payment, RefundRequest


def send_refund_notifications(payment_obj: Payment, booking_obj, booking_type_str: str, refund_request: RefundRequest, extracted_data: dict):
    user_email = None
    booking_reference = "N/A"
    customer_name = "Customer"
    booking_for_email = None

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
            'refunded_amount': extracted_data['refunded_amount_decimal'],
            'booking_reference': booking_reference,
            'customer_name': customer_name,
            'admin_email': getattr(settings, 'ADMIN_EMAIL', settings.DEFAULT_FROM_EMAIL),
            'refund_policy_link': settings.SITE_BASE_URL + '/returns/',
        }
        send_templated_email(
            recipient_list=[user_email],
            subject=f"Your Refund for Booking {booking_reference} Has Been Processed/Updated",
            template_name='user_refund_processed_confirmation.html',
            context=email_context,
            booking=booking_for_email,
            driver_profile=booking_obj.driver_profile if booking_type_str == 'hire_booking' else None,
            service_profile=booking_obj.service_profile if booking_type_str == 'service_booking' else None,
        )

    if settings.ADMIN_EMAIL:
        admin_email_context = {
            'refund_request': refund_request,
            'refunded_amount': extracted_data['refunded_amount_decimal'],
            'booking_reference': booking_reference,
            'stripe_refund_id': extracted_data['stripe_refund_id'],
            'payment_id': payment_obj.id,
            'payment_intent_id': payment_obj.stripe_payment_intent_id,
            'status': extracted_data['refund_status'],
            'event_type': 'charge.refund.updated' if extracted_data['is_refund_object'] else 'charge.refunded',
            'booking_type': booking_type_str,
            'customer_name': customer_name,
        }
        send_templated_email(
            recipient_list=[settings.ADMIN_EMAIL],
            subject=f"Stripe Refund Processed/Updated for {booking_type_str.replace('_', ' ').title()} {booking_reference} (ID: {refund_request.pk if refund_request else 'N/A'})",
            template_name='admin_refund_processed_notification.html',
            context=admin_email_context,
            booking=booking_for_email,
        )
