# payments/utils/refund_creation_utils.py

from payments.models import RefundRequest, Payment
from inventory.models import SalesBooking, SalesProfile # Assuming these are the ones to link
from hire.models import HireBooking, DriverProfile
from service.models import ServiceBooking, ServiceProfile
from django.db import transaction
from django.utils import timezone
from decimal import Decimal


def create_refund_request(
    amount_to_refund,
    reason,
    payment=None,
    hire_booking=None,
    service_booking=None,
    sales_booking=None,
    requesting_user=None, # The Django User object if initiated by a user
    driver_profile=None,
    service_profile=None,
    sales_profile=None,
    is_admin_initiated=False,
    staff_notes=None,
    initial_status='pending', # Default status when creating, can be 'reviewed_pending_approval'
    # Add other fields as needed, e.g., refund_calculation_details
):

    try:
        with transaction.atomic():
            refund_request = RefundRequest.objects.create(
                amount_to_refund=amount_to_refund,
                reason=reason,
                payment=payment,
                hire_booking=hire_booking,
                service_booking=service_booking,
                sales_booking=sales_booking,

                request_email=(requesting_user.email if requesting_user else
                               sales_profile.email if sales_profile else
                               service_profile.email if service_profile else
                               driver_profile.email if driver_profile else None),
                status=initial_status,
                processed_by=requesting_user if is_admin_initiated else None, # Set processed_by if admin initiated
                processed_at=timezone.now() if is_admin_initiated and initial_status in ['approved', 'reviewed_pending_approval'] else None,
                is_admin_initiated=is_admin_initiated,
                staff_notes=staff_notes,
                driver_profile=driver_profile,
                service_profile=service_profile,
                sales_profile=sales_profile,
                # verification_token and token_created_at are handled by save() method of RefundRequest model
            )
            return refund_request
    except Exception as e:
        # In a real application, you might want more robust logging here
        # print(f"Error creating RefundRequest: {e}")
        return None

