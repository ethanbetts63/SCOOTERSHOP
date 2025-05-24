# hire_booking_details_view.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages # Import messages

from hire.models import HireBooking

@user_passes_test(lambda u: u.is_staff)
def hire_booking_details_view(request, pk):
    """
    Displays the detailed information for a single HireBooking.
    """
    booking = get_object_or_404(HireBooking, pk=pk)

    context = {
        'page_title': f'Hire Booking Details - {booking.booking_reference or booking.id}',
        'booking': booking,
    }
    return render(request, 'dashboard/hire_booking_details.html', context)

@user_passes_test(lambda u: u.is_staff)
def delete_hire_booking_view(request, pk):
    """
    Handles the deletion of a HireBooking instance.
    Requires a POST request for security.
    """
    if request.method == 'POST':
        booking = get_object_or_404(HireBooking, pk=pk)
        booking_ref = booking.booking_reference or booking.id # Capture reference before deletion
        try:
            booking.delete()
            messages.success(request, f"Hire Booking {booking_ref} deleted successfully.")
        except Exception as e:
            messages.error(request, f"Error deleting Hire Booking {booking_ref}: {e}")
        return redirect('dashboard:hire_bookings') # Redirect to the calendar view after deletion
    else:
        # If not a POST request, redirect or show an error
        messages.error(request, "Invalid request method for deleting a booking.")
        return redirect('dashboard:hire_bookings') # Or to the details page if you want to show error there
