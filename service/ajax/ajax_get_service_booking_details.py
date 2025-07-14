from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from datetime import datetime
from django.utils import timezone
from service.models import ServiceBooking
from refunds.models import RefundRequest
from refunds.utils.service_refund_calc import calculate_service_refund_amount
from ..decorators import admin_required


@require_GET
@admin_required
def get_service_booking_details_json(request, pk):

    try:
        service_booking = get_object_or_404(ServiceBooking, pk=pk)

        customer_name = "N/A"
        if service_booking.service_profile:
            if service_booking.service_profile.user:
                user_full_name = service_booking.service_profile.user.get_full_name()
                if user_full_name:
                    customer_name = user_full_name
                elif service_booking.service_profile.name:
                    customer_name = service_booking.service_profile.name
            elif service_booking.service_profile.name:
                customer_name = service_booking.service_profile.name

        payment_date = (
            service_booking.payment.created_at.strftime("%Y-%m-%d %H:%M")
            if service_booking.payment and service_booking.payment.created_at
            else "N/A"
        )
        payment_amount = (
            float(service_booking.payment.amount)
            if service_booking.payment and service_booking.payment.amount is not None
            else "N/A"
        )

        motorcycle_details = {
            "year": (
                service_booking.customer_motorcycle.year
                if service_booking.customer_motorcycle
                else "N/A"
            ),
            "brand": (
                service_booking.customer_motorcycle.brand
                if service_booking.customer_motorcycle
                else "N/A"
            ),
            "model": (
                service_booking.customer_motorcycle.model
                if service_booking.customer_motorcycle
                else "N/A"
            ),
        }

        service_type_details = {
            "name": (
                service_booking.service_type.name
                if service_booking.service_type
                else "N/A"
            ),
            "description": (
                service_booking.service_type.description
                if service_booking.service_type
                else "N/A"
            ),
            "base_price": (
                float(service_booking.service_type.base_price)
                if service_booking.service_type
                and service_booking.service_type.base_price is not None
                else "N/A"
            ),
        }

        refund_status_for_booking = "No Refund Request Yet"
        latest_refund_request = (
            RefundRequest.objects.filter(service_booking=service_booking)
            .order_by("-requested_at")
            .first()
        )
        if latest_refund_request:
            refund_status_for_booking = latest_refund_request.get_status_display()

        cancellation_datetime = timezone.now()
        refund_calculation_results = calculate_service_refund_amount(
            booking=service_booking,
            cancellation_datetime=cancellation_datetime,
        )

        booking_details = {
            "id": service_booking.id,
            "service_booking_reference": service_booking.service_booking_reference,
            "customer_name": customer_name,
            "service_date": service_booking.service_date.strftime("%Y-%m-%d"),
            "dropoff_date": service_booking.dropoff_date.strftime("%Y-%m-%d"),
            "dropoff_time": (
                service_booking.dropoff_time.strftime("%H:%M")
                if service_booking.dropoff_time
                else "N/A"
            ),
            "after_hours_drop_off": service_booking.after_hours_drop_off,
            "estimated_pickup_date": (
                service_booking.estimated_pickup_date.strftime("%Y-%m-%d")
                if service_booking.estimated_pickup_date
                else "N/A"
            ),
            "motorcycle_details": motorcycle_details,
            "service_type_details": service_type_details,
            "payment_method": (
                service_booking.get_payment_method_display()
                if service_booking.payment_method
                else "N/A"
            ),
            "payment_date": payment_date,
            "payment_amount": payment_amount,
            "booking_status": service_booking.get_booking_status_display(),
            "payment_status": service_booking.get_payment_status_display(),
            "customer_notes": (
                service_booking.customer_notes if service_booking.customer_notes else ""
            ),
            "service_terms_details": {
                "pk": (
                    service_booking.service_terms_version.pk
                    if service_booking.service_terms_version
                    else None
                ),
                "version_number": (
                    service_booking.service_terms_version.version_number
                    if service_booking.service_terms_version
                    else "N/A"
                ),
            }
            if service_booking.service_terms_version
            else None,
            "entitled_refund_amount": float(
                refund_calculation_results["entitled_amount"]
            ),
            "refund_calculation_details": refund_calculation_results["details"],
            "refund_policy_applied": refund_calculation_results["policy_applied"],
            "refund_days_before_dropoff": refund_calculation_results[
                "days_before_dropoff"
            ],
            "refund_request_status_for_booking": refund_status_for_booking,
        }
        return JsonResponse(booking_details)
    except Http404:
        return JsonResponse({"error": "Service Booking not found"}, status=404)
    except Exception as e:
        return JsonResponse(
            {"error": f"An unexpected error occurred: {str(e)}"}, status=500
        )
