from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test

# This is a placeholder view for the admin booking form.
# We'll add the form logic here later.

def is_staff_or_superuser(user):
    return user.is_staff or user.is_superuser

@user_passes_test(is_staff_or_superuser)
def booking_admin_view(request):
    # In a real application, you would handle form submission here
    # For now, we just render the template
    context = {
        'page_title': 'Admin Service Booking',
    }
    return render(request, 'service/service_booking_admin.html', context)