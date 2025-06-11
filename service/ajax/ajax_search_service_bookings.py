# service/ajax/ajax_search_service_bookings.py

from django.http import JsonResponse
from django.db.models import Q # Import Q for complex lookups
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from service.models import ServiceBooking # Import the ServiceBooking model

@require_GET
@login_required
def search_service_bookings_ajax(request):
    """
    AJAX endpoint to search for ServiceBooking instances based on a query term.
    Searches across booking reference, customer details, motorcycle details,
    and service type details.
    Returns a JSON response with a list of matching bookings.
    """
    # Get the search term from the request, strip whitespace
    search_term = request.GET.get('query', '').strip()
    bookings_data = []

    # Ensure only staff members can access this endpoint
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    if search_term:
        # Build a Q object for complex lookups across multiple fields and related models
        # Use '__icontains' for case-insensitive partial matches
        # Use '__name__icontains' for related model fields (e.g., service_profile__name)
        search_query = (
            Q(service_booking_reference__icontains=search_term) |
            Q(customer_notes__icontains=search_term) |
            Q(booking_status__icontains=search_term) | # Search by status string (e.g., 'pending', 'confirmed')
            Q(payment_status__icontains=search_term) | # Search by payment status string

            # Search related ServiceProfile fields
            Q(service_profile__name__icontains=search_term) |
            Q(service_profile__email__icontains=search_term) |
            Q(service_profile__phone_number__icontains=search_term) |
            # Searching by user's username and email might be redundant if profile name/email covers it,
            # but keep for robustness if users can also be searched directly.
            Q(service_profile__user__username__icontains=search_term) |
            Q(service_profile__user__email__icontains=search_term) |

            # Search related CustomerMotorcycle fields
            # Note: For year, it's a PositiveIntegerField, so __icontains might behave unexpectedly for numbers.
            # However, for simple numeric years, it often works. If not, consider __exact or casting search_term to int.
            Q(customer_motorcycle__year__icontains=search_term) |
            Q(customer_motorcycle__brand__icontains=search_term) |
            Q(customer_motorcycle__model__icontains=search_term) |
            Q(customer_motorcycle__rego__icontains=search_term) |

            # Search related ServiceType fields
            Q(service_type__name__icontains=search_term) |
            Q(service_type__description__icontains=search_term)
        )

        # Filter ServiceBooking objects using the constructed Q object
        # Use .distinct() to avoid duplicate results if a booking matches multiple Q conditions
        # Order by dropoff_date to show more recent bookings first
        queryset = ServiceBooking.objects.filter(search_query).distinct().order_by('-dropoff_date')

        # Limit results to prevent overwhelming the client, adjust as needed
        for booking in queryset[:20]: # Limit to top 20 results
            customer_name = 'N/A'
            if booking.service_profile:
                # Prioritize the ServiceProfile's 'name' field for consistency with test expectations.
                # The ServiceProfile's 'name' is often what the customer entered directly.
                customer_name = booking.service_profile.name
                # The previous logic would sometimes use user.get_full_name() which might differ
                # from profile.name, causing test mismatches.
                # if booking.service_profile.user and booking.service_profile.user.get_full_name():
                #     customer_name = booking.service_profile.user.get_full_name()
                # elif booking.service_profile.name:
                #     customer_name = booking.service_profile.name

            motorcycle_info = 'N/A'
            if booking.customer_motorcycle:
                motorcycle_info = f"{booking.customer_motorcycle.year} {booking.customer_motorcycle.brand} {booking.customer_motorcycle.model}"

            service_type_name = booking.service_type.name if booking.service_type else 'N/A'

            bookings_data.append({
                'id': booking.pk,
                'reference': booking.service_booking_reference,
                'customer_name': customer_name, # This will now consistently use service_profile.name
                'dropoff_date': booking.dropoff_date.strftime('%Y-%m-%d'),
                'dropoff_time': booking.dropoff_time.strftime('%H:%M'),
                'service_type_name': service_type_name,
                'motorcycle_info': motorcycle_info,
                'booking_status': booking.get_booking_status_display(),
                'payment_status': booking.get_payment_status_display(),
                # Add more fields if needed for your search result display
            })

    # Return the results as a JSON response
    return JsonResponse({'bookings': bookings_data})
