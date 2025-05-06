# service/views/booking_admin_anon.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.urls import reverse

# Import the new form
from service.forms import AdminAnonBookingForm
from service.models import ServiceBooking, ServiceType
# No User or CustomerMotorcycle model needed for direct creation for anon flow.

def is_staff_or_superuser(user):
    """Check if the user is staff or a superuser."""
    return user.is_active and (user.is_staff or user.is_superuser)

@user_passes_test(is_staff_or_superuser)
def booking_admin_anon_view(request):
    if request.method == 'POST':
        # Use the new form for anonymous bookings
        form = AdminAnonBookingForm(request.POST)
        if form.is_valid():
            # Extract one-off customer details from the new form
            first_name = form.cleaned_data['one_off_first_name']
            last_name = form.cleaned_data['one_off_last_name']
            email = form.cleaned_data['one_off_email']
            phone_number = form.cleaned_data.get('one_off_phone_number', '')

            # Extract anonymous vehicle details from the new form
            anon_vehicle_make = form.cleaned_data.get('anon_vehicle_make')
            anon_vehicle_model = form.cleaned_data.get('anon_vehicle_model')
            anon_vehicle_year = form.cleaned_data.get('anon_vehicle_year')
            anon_vehicle_rego = form.cleaned_data.get('anon_vehicle_rego', '')
            anon_vehicle_odometer = form.cleaned_data.get('anon_vehicle_odometer')
            anon_vehicle_transmission = form.cleaned_data.get('anon_vehicle_transmission', '')

            # Extract service details
            service_type = form.cleaned_data['service_type']
            appointment_datetime = form.cleaned_data['appointment_datetime']
            preferred_contact = form.cleaned_data['preferred_contact']
            booking_comments = form.cleaned_data.get('booking_comments', '')

            # Create the ServiceBooking instance for an anonymous user
            booking = ServiceBooking(
                customer=None,  # Explicitly no user linked
                customer_name=f"{first_name} {last_name}",
                customer_email=email,
                customer_phone=phone_number,

                # Anonymous vehicle details directly on the booking
                anon_vehicle_make=anon_vehicle_make,
                anon_vehicle_model=anon_vehicle_model,
                anon_vehicle_year=anon_vehicle_year,
                anon_vehicle_rego=anon_vehicle_rego,
                anon_vehicle_odometer=anon_vehicle_odometer,
                anon_vehicle_transmission=anon_vehicle_transmission,

                vehicle=None, # No CustomerMotorcycle linked

                service_type=service_type,
                appointment_datetime=appointment_datetime,
                preferred_contact=preferred_contact,
                customer_notes=booking_comments,
                status='pending', # Default status
            )
            booking.save()

            messages.success(request, f"One-off service booking created successfully for {first_name} {last_name}.")
            return redirect(reverse('service:admin_booking_anon')) # Redirect back to this form or a success page

        else:
            messages.error(request, "Please correct the errors below.")

    else: # GET request
        # Use the new form for anonymous bookings
        form = AdminAnonBookingForm()

    context = {
        'page_title': 'Admin Service Booking for Anonymous/One-off Customer',
        'form': form,
    }
    return render(request, 'service/service_booking_admin_anon.html', context)