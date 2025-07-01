                              
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages                  

from hire.models import HireBooking

@user_passes_test(lambda u: u.is_staff)
def hire_booking_details_view(request, pk):
    """
    Displays the detailed information for a single HireBooking.
    """
    booking = get_object_or_404(HireBooking, pk=pk)

                                                                            
    refund_policy_snapshot = None
    if booking.payment:
        refund_policy_snapshot = booking.payment.refund_policy_snapshot
    else:
        messages.warning(request, "No payment record found for this booking, so no refund policy snapshot is available.")

    context = {
        'page_title': f'Hire Booking Details - {booking.booking_reference or booking.id}',
        'booking': booking,
        'refund_policy_snapshot': refund_policy_snapshot,                                    
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
        booking_ref = booking.booking_reference or booking.id                                    
        try:
            booking.delete()
            messages.success(request, f"Hire Booking {booking_ref} deleted successfully.")
        except Exception as e:
            messages.error(request, f"Error deleting Hire Booking {booking_ref}: {e}")
        return redirect('dashboard:hire_bookings')                                               
    else:
                                                          
        messages.error(request, "Invalid request method for deleting a booking.")
        return redirect('dashboard:hire_bookings')                                                         
