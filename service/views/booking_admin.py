# service/booking_admin.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from service.forms import AdminBookingForm, CustomerMotorcycleForm
from service.models import ServiceBooking, CustomerMotorcycle, ServiceType
from users.models import User
from django.shortcuts import get_object_or_404


def is_staff_or_superuser(user):
    """Check if the user is staff or a superuser."""
    return user.is_staff or user.is_superuser

@user_passes_test(is_staff_or_superuser)
def booking_admin_view(request):
    if request.method == 'POST':
        form = AdminBookingForm(request.POST)
        if form.is_valid():
            customer_type = form.cleaned_data['customer_type']
            
            # Process customer details
            if customer_type == 'existing':
                user = form.cleaned_data['user']
                # Update existing user with form data if needed
                user.first_name = form.cleaned_data.get('one_off_first_name', user.first_name)
                user.last_name = form.cleaned_data.get('one_off_last_name', user.last_name)
                user.email = form.cleaned_data.get('one_off_email', user.email)
                if hasattr(user, 'phone_number'):
                    user.phone_number = form.cleaned_data.get('one_off_phone_number', user.phone_number)
                user.save()
            else:  # one_off
                # Create a new anonymous user or handle one-off booking
                first_name = form.cleaned_data['one_off_first_name']
                last_name = form.cleaned_data['one_off_last_name']
                email = form.cleaned_data['one_off_email']
                phone_number = form.cleaned_data.get('one_off_phone_number', '')
                
                # For one-off bookings, create a booking without a user account
                user = None
                
                # Create anonymous vehicle data
                anon_vehicle_make = form.cleaned_data.get('anon_vehicle_make')
                anon_vehicle_model = form.cleaned_data.get('anon_vehicle_model')
                anon_vehicle_year = form.cleaned_data.get('anon_vehicle_year')
                
                # Create a booking with anonymous details
                booking = ServiceBooking(
                    customer=None,  # No user account
                    customer_name=f"{first_name} {last_name}",
                    customer_email=email,
                    customer_phone=phone_number,
                    vehicle_make=anon_vehicle_make,
                    vehicle_model=anon_vehicle_model,
                    vehicle_year=anon_vehicle_year,
                    service_type=form.cleaned_data['service_type'],
                    appointment_datetime=form.cleaned_data['appointment_datetime'],
                    preferred_contact=form.cleaned_data['preferred_contact'],
                    customer_notes=form.cleaned_data.get('booking_comments', ''),
                    status='pending',
                )
                booking.save()
                
                messages.success(request, f"One-off service booking created successfully for {first_name} {last_name}.")
                return redirect(reverse('service:admin_booking'))

            # For existing users, handle motorcycle and create booking
            if customer_type == 'existing' and user:
                bike_selection_type = form.cleaned_data['bike_selection_type']
                service_type = form.cleaned_data['service_type']
                appointment_datetime = form.cleaned_data['appointment_datetime']
                preferred_contact = form.cleaned_data['preferred_contact']
                booking_comments = form.cleaned_data.get('booking_comments', '')

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
                        rego=form.cleaned_data.get('new_bike_rego', ''),
                        vin_number=form.cleaned_data.get('new_bike_vin_number', ''),
                        odometer=form.cleaned_data.get('new_bike_odometer', 0),
                        transmission=form.cleaned_data.get('new_bike_transmission', ''),
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
                    status='pending',
                )
                booking.save()

                messages.success(request, f"Service booking created successfully for {user.get_full_name() or user.username}.")
                # Redirect to a confirmation page or the admin bookings list
                return redirect(reverse('service:admin_booking'))

        else:
            # Form is invalid, render with errors
            messages.error(request, "Please correct the errors below.")

    else:  # GET request
        form = AdminBookingForm()

    context = {
        'page_title': 'Admin Service Booking',
        'form': form,
    }
    return render(request, 'service/service_booking_admin.html', context)

@user_passes_test(is_staff_or_superuser)
@require_GET
def get_user_details(request, user_id):
    """AJAX endpoint to get user details for the booking form."""
    try:
        user = get_object_or_404(User, id=user_id) # Using get_object_or_404
        data = {
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'phone_number': getattr(user, 'phone_number', '')
        }
        return JsonResponse(data)
    except Exception as e: # Catching other potential exceptions
        return JsonResponse({'error': str(e)}, status=500)

@user_passes_test(is_staff_or_superuser)
@require_GET
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
                    'rego': bike.rego or '', # Use empty string for consistency
                    'vin_number': bike.vin_number or '',
                    'odometer': bike.odometer or 0,
                    'transmission': bike.transmission or '',
                } for bike in motorcycles
            ]
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@user_passes_test(is_staff_or_superuser)
@require_GET
def get_motorcycle_details(request, motorcycle_id):
    """AJAX endpoint to get details for a specific motorcycle."""
    try:
        motorcycle = get_object_or_404(CustomerMotorcycle, id=motorcycle_id)
        data = {
            'make': motorcycle.make,
            'model': motorcycle.model,
            'year': motorcycle.year,
            'rego': motorcycle.rego or '',
            'vin_number': motorcycle.vin_number or '',
            'odometer': motorcycle.odometer or 0,
            'transmission': motorcycle.transmission or '',
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)