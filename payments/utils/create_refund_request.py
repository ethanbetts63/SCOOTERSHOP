from payments.models import RefundRequest, Payment
from django.db import transaction
from django.utils import timezone
from decimal import Decimal


def create_refund_request(
    amount_to_refund,
    reason,
    payment=None,
    service_booking=None,
    sales_booking=None,
    requesting_user=None,
    service_profile=None,
    sales_profile=None,
    is_admin_initiated=False,
    staff_notes=None,
    initial_status="pending",
):

    try:
        with transaction.atomic():
            refund_request = RefundRequest.objects.create(
                amount_to_refund=amount_to_refund,
                reason=reason,
                payment=payment,
                service_booking=service_booking,
                sales_booking=sales_booking,
                request_email=(
                    requesting_user.email
                    if requesting_user
                    else (
                        sales_profile.email
                        if sales_profile
                        else service_profile.email if service_profile else None
                    )
                ),
                status=initial_status,
                processed_by=requesting_user if is_admin_initiated else None,
                processed_at=(
                    timezone.now()
                    if is_admin_initiated
                    and initial_status in ["approved", "reviewed_pending_approval"]
                    else None
                ),
                is_admin_initiated=is_admin_initiated,
                staff_notes=staff_notes,
                service_profile=service_profile,
                sales_profile=sales_profile,
            )
            return refund_request
    except Exception as e:

        return None
