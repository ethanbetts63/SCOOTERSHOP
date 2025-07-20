from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET
from django.utils import timezone
from inventory.decorators import admin_required

from inventory.models import SalesBooking
from refunds.models import RefundRequest
from refunds.utils.sales_refund_calc import calculate_sales_refund_amount


@require_GET
@admin_required
def get_sales_booking_details_json(request, pk):
    try:
        sales_booking = get_object_or_404(SalesBooking, pk=pk)

        customer_name = "N/A"
        customer_email = "N/A"

        if sales_booking.sales_profile:
            if sales_booking.sales_profile.user:
                user_obj = sales_booking.sales_profile.user
                customer_name = user_obj.get_full_name() or user_obj.email
                customer_email = user_obj.email
            else:
                customer_name = (
                    sales_booking.sales_profile.name
                    if sales_booking.sales_profile.name
                    else "N/A"
                )
                customer_email = (
                    sales_booking.sales_profile.email
                    if sales_booking.sales_profile.email
                    else "N/A"
                )

        motorcycle_details = {
            "year": (
                sales_booking.motorcycle.year if sales_booking.motorcycle else "N/A"
            ),
            "brand": (
                sales_booking.motorcycle.brand if sales_booking.motorcycle else "N/A"
            ),
            "model": (
                sales_booking.motorcycle.model if sales_booking.motorcycle else "N/A"
            ),
            "vin": (
                sales_booking.motorcycle.vin_number
                if sales_booking.motorcycle
                else "N/A"
            ),
        }

        payment_date = (
            sales_booking.payment.created_at.strftime("%Y-%m-%d %H:%M")
            if sales_booking.payment and sales_booking.payment.created_at
            else "N/A"
        )
        payment_amount = (
            float(sales_booking.payment.amount)
            if sales_booking.payment and sales_booking.payment.amount is not None
            else "N/A"
        )

        refund_status_for_booking = "No Refund Request Yet"
        latest_refund_request = (
            RefundRequest.objects.filter(sales_booking=sales_booking)
            .order_by("-requested_at")
            .first()
        )
        if latest_refund_request:
            refund_status_for_booking = latest_refund_request.get_status_display()

        cancellation_datetime_for_calc = timezone.now()

        refund_calculation_results = calculate_sales_refund_amount(
            booking=sales_booking,
            cancellation_datetime=cancellation_datetime_for_calc,
        )

        booking_details = {
            "id": sales_booking.id,
            "sales_booking_reference": sales_booking.sales_booking_reference,
            "customer_name": customer_name,
            "customer_email": customer_email,
            "motorcycle_details": motorcycle_details,
            "payment_date": payment_date,
            "payment_amount": payment_amount,
            "booking_status": sales_booking.get_booking_status_display(),
            "payment_status": sales_booking.get_payment_status_display(),
            "customer_notes": sales_booking.customer_notes or "",
            "appointment_date": sales_booking.appointment_date.strftime("%Y-%m-%d") if sales_booking.appointment_date else "N/A",
            "appointment_time": sales_booking.appointment_time.strftime("%H:%M") if sales_booking.appointment_time else "N/A",
            "entitled_refund_amount": float(
                refund_calculation_results["entitled_amount"]
            ),
            "refund_calculation_details": refund_calculation_results["details"],
            "refund_policy_applied": refund_calculation_results["policy_applied"],
            "days_until_booking": float(refund_calculation_results.get("days_until_booking", 0)),
            "refund_request_status_for_booking": refund_status_for_booking,
        }
        return JsonResponse(booking_details)
    except Http404:
        return JsonResponse({"error": "Sales Booking not found"}, status=404)
    except Exception as e:
        return JsonResponse(
            {"error": f"An unexpected error occurred: {str(e)}"}, status=500
        )
