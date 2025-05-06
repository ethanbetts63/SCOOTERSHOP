# service/booking_admin.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.http import JsonResponse
from service.forms import AdminBookingForm, CustomerMotorcycleForm
from service.models import ServiceBooking, CustomerMotorcycle
from users.models import User


def is_staff_or_superuser(user):
    """Check if the user is staff or a superuser."""
    return user.is_staff or user.is_superuser

@user_passes_test(is_staff_or_superuser)
def booking_admin_view(request):
    if request.method == 'POST':
        form = AdminBookingForm(request.POST)
        if form.is_valid():
            # Process the valid form data
            user = form.cleaned_data['user']
            bike_selection_type = form.cleaned_data['bike_selection_type']
            service_type = form.cleaned_data['service_type']
            appointment_datetime = form.cleaned_data['appointment_datetime']
            preferred_contact = form.cleaned_data['preferred_contact']
            booking_comments = form.cleaned_data['booking_comments']

            motorcycle_instance = None

            if bike_selection_type == 'existing':
                motorcycle_instance = form.cleaned_data['existing_motorcycle']
            elif bike_selection_type == 'new':
                # Create a new CustomerMotorcycle instance
                motorcycle_instance = CustomerMotorcycle(
                    owner=user,
                    make=form.cleaned_data['new_bike_make'],
                    model=form.cleaned_data['new_bike_model'],
                    year=form.cleaned_data['new_bike_year'],
                    rego=form.cleaned_data.get('new_bike_rego'),
                    vin_number=form.cleaned_data.get('new_bike_vin_number'),
                    odometer=form.cleaned_data.get('new_bike_odometer'),
                    transmission=form.cleaned_data.get('new_bike_transmission'),
                )
                motorcycle_instance.save()
                messages.success(request, f"New motorcycle added for {user.get_full_name() or user.username}.")


            # Create the ServiceBooking instance
            booking = ServiceBooking(
                customer=user,
                vehicle=motorcycle_instance,
                service_type=service_type,
                appointment_datetime=appointment_datetime,
                preferred_contact=preferred_contact,
                customer_notes=booking_comments,
                status='pending', # Or set a default status appropriate for admin bookings
            )
            booking.save()

            messages.success(request, f"Service booking created successfully for {user.get_full_name() or user.username}.")
            # Redirect to a confirmation page or the admin bookings list
            return redirect(reverse('service:admin_booking')) # Redirect back to the form for another booking

        else:
            # Form is invalid, render with errors
            messages.error(request, "Please correct the errors below.")

    else: # GET request
        form = AdminBookingForm()

    context = {
        'page_title': 'Admin Service Booking',
        'form': form,
    }
    return render(request, 'service/service_booking_admin.html', context)

@user_passes_test(is_staff_or_superuser)
def get_user_details(request, user_id):
    """AJAX endpoint to get user details for the booking form."""
    try:
        user = User.objects.get(id=user_id)
        data = {
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'phone_number': getattr(user, 'phone_number', '')  # In case phone_number field exists on User model
        }
        return JsonResponse(data)
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)

@user_passes_test(is_staff_or_superuser)
def get_user_motorcycles(request, user_id):
    """AJAX endpoint to get a user's motorcycles for the booking form."""
    try:
        motorcycles = CustomerMotorcycle.objects.filter(owner_id=user_id)
        data = {
            'motorcycles': [
                {
                    'id': bike.id,
                    'make': bike.make,
                    'model': bike.model,
                    'year': bike.year,
                    'rego': bike.rego or 'No Rego'
                } for bike in motorcycles
            ]
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)