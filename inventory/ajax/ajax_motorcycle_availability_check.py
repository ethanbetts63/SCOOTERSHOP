from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json

from inventory.models import TempSalesBooking, Motorcycle
from django.db import transaction


@csrf_exempt
@require_POST
def check_motorcycle_availability(request):
    try:
        data = json.loads(request.body)
        temp_booking_uuid = data.get("temp_booking_uuid")

        if not temp_booking_uuid:
            return JsonResponse(
                {"available": False, "message": "Temporary booking ID is required."},
                status=400,
            )

        with transaction.atomic():
            try:
                temp_booking = get_object_or_404(
                    TempSalesBooking, session_uuid=temp_booking_uuid
                )
            except Http404:
                return JsonResponse(
                    {"available": False, "message": "Temporary booking not found."},
                    status=404,
                )

            try:
                motorcycle = get_object_or_404(
                    Motorcycle.objects.select_for_update(),
                    pk=temp_booking.motorcycle_id,
                )
            except Http404:
                return JsonResponse(
                    {"available": False, "message": "Associated motorcycle not found."},
                    status=404,
                )

            if not motorcycle.is_available:
                return JsonResponse(
                    {
                        "available": False,
                        "message": "Sorry, this motorcycle has just been reserved or sold.",
                    }
                )

            return JsonResponse(
                {"available": True, "message": "Motorcycle is available."}
            )

    except json.JSONDecodeError:
        return JsonResponse(
            {"available": False, "message": "Invalid JSON format."}, status=400
        )
    except Exception as e:
        return JsonResponse(
            {"available": False, "message": f"An unexpected error occurred: {str(e)}"},
            status=500,
        )
