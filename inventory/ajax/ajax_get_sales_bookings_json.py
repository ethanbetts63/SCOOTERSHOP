from django.http import JsonResponse
from inventory.models import SalesBooking
from django.urls import reverse

def get_sales_bookings_json(request):
    bookings = SalesBooking.objects.all()
    events = []
    for booking in bookings:
        if booking.appointment_date and booking.appointment_time:
            events.append({
                'title': f"{booking.sales_profile.name} - {booking.motorcycle.title}",
                'start': f"{booking.appointment_date.isoformat()}T{booking.appointment_time.isoformat()}",
                'url': reverse('inventory:sales_booking_details', kwargs={'pk': booking.pk}),
                'status': booking.get_booking_status_display(),
            })
    return JsonResponse(events, safe=False)