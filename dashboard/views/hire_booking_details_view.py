# hire_booking_details_view.py
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import user_passes_test

from hire.models import HireBooking

@user_passes_test(lambda u: u.is_staff)
def hire_booking_details_view(request, pk):
    booking = get_object_or_404(HireBooking, pk=pk)

    context = {
        'page_title': f'Hire Booking Details - {booking.booking_reference or booking.id}',
        'booking': booking,
    }
    return render(request, 'dashboard/hire_booking_details.html', context)
