from django.utils import timezone
from payments.models import Payment

from refunds.models import RefundRequest


def process_refund_request_entry(
    payment_obj: Payment, booking_obj, booking_type_str: str, extracted_data: dict
):
    stripe_refund_id = extracted_data["stripe_refund_id"]
    refunded_amount_decimal = extracted_data["refunded_amount_decimal"]

    refund_request = (
        RefundRequest.objects.filter(
            payment=payment_obj,
            status__in=[
                "pending",
                "approved",
                "reviewed_pending_approval",
                "partially_refunded",
                "unverified",
                "failed",
            ],
        )
        .order_by("-requested_at")
        .first()
    )

    if not refund_request:
        refund_request = RefundRequest.objects.create(
            payment=payment_obj,
            service_booking=(
                booking_obj if booking_type_str == "service_booking" else None
            ),
            sales_booking=booking_obj if booking_type_str == "sales_booking" else None,
            stripe_refund_id=stripe_refund_id,
            amount_to_refund=refunded_amount_decimal,
            status=(
                "refunded" if payment_obj.status == "refunded" else "partially_refunded"
            ),
            is_admin_initiated=True,
            processed_at=timezone.now(),
        )
    else:
        refund_request.stripe_refund_id = (
            stripe_refund_id if stripe_refund_id else refund_request.stripe_refund_id
        )
        refund_request.amount_to_refund = refunded_amount_decimal
        refund_request.status = (
            "refunded" if payment_obj.status == "refunded" else "partially_refunded"
        )
        refund_request.processed_at = timezone.now()
        refund_request.save()

    return refund_request
