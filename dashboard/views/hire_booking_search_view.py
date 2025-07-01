                             
from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Q

from hire.models import HireBooking

@user_passes_test(lambda u: u.is_staff)
def hire_booking_search_view(request):
    query = request.GET.get('q')
    sort_by = request.GET.get('sort_by', '-pickup_date')

    booking_statuses = getattr(HireBooking, 'STATUS_CHOICES', [])
    all_status_values = [status[0] for status in booking_statuses]

    if 'status' not in request.GET:
        selected_statuses = all_status_values
    else:
        selected_statuses = request.GET.getlist('status')

    hire_bookings = HireBooking.objects.all()

    if selected_statuses:
        if hasattr(HireBooking, 'status'):
             hire_bookings = hire_bookings.filter(status__in=selected_statuses)
        else:
             messages.warning(request, "Status filtering is not available for Hire Bookings.")
             selected_statuses = []

    if query:
        search_filter = Q()

        search_filter |= Q(driver_profile__user__first_name__icontains=query)
        search_filter |= Q(driver_profile__user__last_name__icontains=query)
        search_filter |= Q(driver_profile__user__email__icontains=query)
        search_filter |= Q(booking_reference__icontains=query)

        search_filter |= Q(motorcycle__name__icontains=query)
        search_filter |= Q(motorcycle__license_plate__icontains=query)

        search_filter |= Q(customer_notes__icontains=query)
        search_filter |= Q(internal_notes__icontains=query)

        hire_bookings = hire_bookings.filter(search_filter)

    if sort_by == 'id':
        hire_bookings = hire_bookings.order_by('id')
    elif sort_by == '-id':
        hire_bookings = hire_bookings.order_by('-id')
    elif sort_by == 'pickup_date':
        hire_bookings = hire_bookings.order_by('pickup_date')
    elif sort_by == '-pickup_date':
        hire_bookings = hire_bookings.order_by('-pickup_date')
    elif sort_by == 'return_date':
         if hasattr(HireBooking, 'return_date'):
              hire_bookings = hire_bookings.order_by('return_date')
    elif sort_by == '-return_date':
         if hasattr(HireBooking, 'return_date'):
              hire_bookings = hire_bookings.order_by('-return_date')
    elif sort_by == 'date_created':
        hire_bookings = hire_bookings.order_by('created_at')
    elif sort_by == '-date_created':
        hire_bookings = hire_bookings.order_by('-created_at')

    context = {
        'page_title': 'Hire Booking Search',
        'bookings': hire_bookings,
        'query': query,
        'sort_by': sort_by,
        'selected_statuses': selected_statuses,
        'booking_statuses': booking_statuses,
    }
    return render(request, 'dashboard/hire_booking_search.html', context)
