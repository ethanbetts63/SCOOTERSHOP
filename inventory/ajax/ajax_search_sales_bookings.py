from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.http import require_GET
from ..decorators import admin_required
from inventory.models import SalesBooking


@require_GET
@admin_required
def search_sales_bookings_ajax(request):
    search_term = request.GET.get("query", "").strip()
    bookings_data = []

    print(f"DEBUG: search_sales_bookings_ajax - search_term: {search_term}")

    if search_term:
        search_query = (
            Q(sales_booking_reference__icontains=search_term)
            | Q(customer_notes__icontains=search_term)
            | Q(booking_status__icontains=search_term)
            | Q(payment_status__icontains=search_term)
            | Q(sales_profile__name__icontains=search_term)
            | Q(sales_profile__email__icontains=search_term)
            | Q(sales_profile__phone_number__icontains=search_term)
            | Q(sales_profile__user__username__icontains=search_term)
            | Q(sales_profile__user__email__icontains=search_term)
            | Q(motorcycle__brand__icontains=search_term)
            | Q(motorcycle__model__icontains=search_term)
            | Q(motorcycle__year__icontains=search_term)
        )

        queryset = (
            SalesBooking.objects.filter(search_query).distinct().order_by("-created_at")
        )
        print(f"DEBUG: search_sales_bookings_ajax - Queryset count: {queryset.count()}")
        print(f"DEBUG: search_sales_bookings_ajax - Queryset first 5: {list(queryset[:5])}")

        for booking in queryset[:20]:
            customer_name = (
                booking.sales_profile.name if booking.sales_profile else "N/A"
            )
            motorcycle_info = (
                f"{booking.motorcycle.year} {booking.motorcycle.brand} {booking.motorcycle.model}"
                if booking.motorcycle
                else "N/A"
            )

            bookings_data.append(
                {
                    "id": booking.pk,
                    "reference": booking.sales_booking_reference,
                    "customer_name": customer_name,
                    "motorcycle_info": motorcycle_info,
                    "booking_status": booking.get_booking_status_display(),
                    "payment_status": booking.get_payment_status_display(),
                }
            )
        print(f"DEBUG: search_sales_bookings_ajax - Bookings data length: {len(bookings_data)}")
        print(f"DEBUG: search_sales_bookings_ajax - Bookings data (first item): {bookings_data[0] if bookings_data else 'N/A'}")

    return JsonResponse({"bookings": bookings_data})
