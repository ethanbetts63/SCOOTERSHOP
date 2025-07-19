from django.http import JsonResponse
from django.views.decorators.http import require_GET
from inventory.models import SalesBooking
from service.models import ServiceBooking
from inventory.ajax.ajax_get_sales_booking_details import get_sales_booking_details_json
from service.ajax.ajax_get_service_booking_details import get_service_booking_details_json
import re

from refunds.decorators import admin_required

@require_GET
@admin_required
def get_booking_details_by_reference(request):
    booking_reference = request.GET.get("booking_reference")
    if not booking_reference:
        return JsonResponse({"error": "Booking reference is required."}, status=400)

    if re.match(r"^(SERVICE|SVC)-\w+", booking_reference, re.IGNORECASE):
        try:
            booking = ServiceBooking.objects.get(service_booking_reference__iexact=booking_reference)
            return get_service_booking_details_json(request, booking.pk)
        except ServiceBooking.DoesNotExist:
            return JsonResponse({"error": "Service booking not found."}, status=404)
    elif re.match(r"^SBK-\w+", booking_reference, re.IGNORECASE):
        try:
            booking = SalesBooking.objects.get(sales_booking_reference__iexact=booking_reference)
            return get_sales_booking_details_json(request, booking.pk)
        except SalesBooking.DoesNotExist:
            return JsonResponse({"error": "Sales booking not found."}, status=404)
    else:
        return JsonResponse({"error": "Invalid booking reference format."}, status=400)
