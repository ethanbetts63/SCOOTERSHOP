from django.db import transaction
import logging

logger = logging.getLogger(__name__)


from ..utils.get_booking_from_payment import get_booking_from_payment
from refunds.utils.extract_stripe_refund_data import extract_stripe_refund_data
from ..utils.update_associated_bookings_and_payments import (
    update_associated_bookings_and_payments,
)
from refunds.utils.process_refund_request_entry import process_refund_request_entry
from refunds.utils.send_refund_notification import send_refund_notifications
from ..models import Payment


def handle_booking_refunded(payment_obj: Payment, event_object_data: dict):
    with transaction.atomic():
        try:
            extracted_data = extract_stripe_refund_data(event_object_data)
        except Exception as e:
            logger.error(f"Error extracting Stripe refund data: {e}")
            raise

        if extracted_data["refunded_amount_decimal"] <= 0 or (
            not extracted_data["is_charge_object"]
            and not extracted_data["is_refund_object"]
            and not extracted_data["is_payment_intent_object"]
        ):
            return

        try:
            booking_obj, booking_type_str = get_booking_from_payment(payment_obj)
        except Exception as e:
            logger.error(f"Error in get_booking_from_payment: {e}")
            raise

        try:
            update_associated_bookings_and_payments(
                payment_obj,
                booking_obj,
                booking_type_str,
                extracted_data["refunded_amount_decimal"],
            )
        except Exception as e:
            logger.error(f"Error in update_associated_bookings_and_payments: {e}")
            raise

        try:
            refund_request = process_refund_request_entry(
                payment_obj, booking_obj, booking_type_str, extracted_data
            )
        except Exception as e:
            logger.error(f"Error in process_refund_request_entry: {e}")
            raise

        try:
            send_refund_notifications(
                payment_obj,
                booking_obj,
                booking_type_str,
                refund_request,
                extracted_data,
            )
        except Exception as e:
            logger.error(f"Error in send_refund_notifications: {e}")
            raise


def handle_booking_refund_updated(payment_obj: Payment, event_data: dict):
    handle_booking_refunded(payment_obj, event_data)
