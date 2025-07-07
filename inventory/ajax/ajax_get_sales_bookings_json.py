from django.http import JsonResponse
from inventory.models import SalesBooking
from django.urls import reverse

def get_sales_bookings_json(request):
    if not request.user.is_staff:
        return JsonResponse({"error": "Permission denied"}, status=403)

    bookings = SalesBooking.objects.filter(
        booking_status__in=["confirmed", "completed"]
    ).select_related('motorcycle', 'sales_profile')

    events = []
    for booking in bookings:
        if booking.appointment_date and booking.appointment_time:
            events.append({
                'title': f"{booking.sales_profile.name} - {booking.motorcycle.title}",
                'start': f"{booking.appointment_date.isoformat()}T{booking.appointment_time.isoformat()}",
                'url': reverse('inventory:sales_booking_details', kwargs={'pk': booking.pk}),
                'className': f"status-{booking.booking_status}",
                'allDay': False
            })
            
    return JsonResponse(events, safe=False)
