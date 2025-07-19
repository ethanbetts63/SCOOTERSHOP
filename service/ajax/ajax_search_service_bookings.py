from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.http import require_GET
from service.models import ServiceBooking
from ..decorators import admin_required


@require_GET
@admin_required
def search_service_bookings_ajax(request):
    search_term = request.GET.get("query", "").strip()
    bookings_data = []

    print(f"DEBUG: search_service_bookings_ajax - search_term: {search_term}")

    if not request.user.is_staff:
        print("DEBUG: search_service_bookings_ajax - Permission denied (not staff)")
        return JsonResponse({"error": "Permission denied"}, status=403)

    if search_term:
        search_query = (
            Q(service_booking_reference__icontains=search_term)
            | Q(customer_notes__icontains=search_term)
            | Q(booking_status__icontains=search_term)
            | Q(payment_status__icontains=search_term)
            | Q(service_profile__name__icontains=search_term)
            | Q(service_profile__email__icontains=search_term)
            | Q(service_profile__phone_number__icontains=search_term)
            | Q(service_profile__user__username__icontains=search_term)
            | Q(service_profile__user__email__icontains=search_term)
            | Q(customer_motorcycle__year__icontains=search_term)
            | Q(customer_motorcycle__brand__icontains=search_term)
            | Q(customer_motorcycle__model__icontains=search_term)
            | Q(customer_motorcycle__rego__icontains=search_term)
            | Q(service_type__name__icontains=search_term)
            | Q(service_type__description__icontains=search_term)
        )

        queryset = (
            ServiceBooking.objects.filter(search_query)
            .distinct()
            .order_by("-dropoff_date")
        )
        print(f"DEBUG: search_service_bookings_ajax - Queryset count: {queryset.count()}")
        print(f"DEBUG: search_service_bookings_ajax - Queryset first 5: {list(queryset[:5])}")


        for booking in queryset[:20]:
            customer_name = "N/A"
            if booking.service_profile:
                customer_name = booking.service_profile.name

            motorcycle_info = "N/A"
            if booking.customer_motorcycle:
                motorcycle_info = f"{booking.customer_motorcycle.year} {booking.customer_motorcycle.brand} {booking.customer_motorcycle.model}"

            service_type_name = (
                booking.service_type.name if booking.service_type else "N/A"
            )

            bookings_data.append(
                {
                    "id": booking.pk,
                    "reference": booking.service_booking_reference,
                    "customer_name": customer_name,
                    "dropoff_date": booking.dropoff_date.strftime("%Y-%m-%d"),
                    "dropoff_time": booking.dropoff_time.strftime("%H:%M"),
                    "service_type_name": service_type_name,
                    "motorcycle_info": motorcycle_info,
                    "booking_status": booking.get_booking_status_display(),
                    "payment_status": booking.get_payment_status_display(),
                }
            )
        print(f"DEBUG: search_service_bookings_ajax - Bookings data length: {len(bookings_data)}")
        print(f"DEBUG: search_service_bookings_ajax - Bookings data (first item): {bookings_data[0] if bookings_data else 'N/A'}")

    return JsonResponse({"bookings": bookings_data})
