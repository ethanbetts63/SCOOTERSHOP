# service/views/booking_admin_user.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.urls import reverse
from django.http import JsonResponse
from django.views.decorators.http import require_GET

# Import the new form
from service.forms import AdminUserBookingForm
from service.models import ServiceBooking, CustomerMotorcycle, ServiceType
from users.models import User # Ensure User model is correctly imported

def is_staff_or_superuser(user):
    """Check if the user is staff or a superuser."""
    return user.is_active and (user.is_staff or user.is_superuser)

@user_passes_test(is_staff_or_superuser)
def booking_admin_user_view(request):
    user_id = request.POST.get('user') if request.method == 'POST' else None
    user_instance = None
    if user_id:
        try:
            user_instance = User.objects.get(id=user_id)
        except User.DoesNotExist:
            pass # Handle case where user ID is in POST but user doesn't exist

    if request.method == 'POST':
        # Use the new form for existing user bookings
        form = AdminUserBookingForm(request.POST)
        # If user was selected, ensure their motorcycles are available for validation
        if user_instance:
             form.fields['existing_motorcycle'].queryset = CustomerMotorcycle.objects.filter(owner=user_instance).order_by('make', 'model')

        if form.is_valid():
            user = form.cleaned_data.get('user')

            # --- Update User Details ---
            # Retrieve the user instance again to ensure we have the latest version
            user_to_update = get_object_or_404(User, id=user.id)

            # Update user fields if they are provided in the form
            if form.cleaned_data.get('user_first_name'):
                user_to_update.first_name = form.cleaned_data['user_first_name']
            if form.cleaned_data.get('user_last_name'):
                user_to_update.last_name = form.cleaned_data['user_last_name']
            if form.cleaned_data.get('user_email'):
                user_to_update.email = form.cleaned_data['user_email']
            if form.cleaned_data.get('user_phone_number'):
                 # Assuming 'phone_number' is a field on your User model
                 # Use setattr for safety if the field might not exist
                 setattr(user_to_update, 'phone_number', form.cleaned_data['user_phone_number'])

            # Save the updated user instance
            user_to_update.save()
            messages.success(request, f"User details updated for {user_to_update.get_full_name() or user_to_update.username}.")
            # --- End Update User Details ---


            bike_selection_type = form.cleaned_data['bike_selection_type']
            service_type = form.cleaned_data['service_type']
            appointment_datetime = form.cleaned_data['appointment_datetime']
            preferred_contact = form.cleaned_data['preferred_contact']
            booking_comments = form.cleaned_data.get('booking_comments', '')

            motorcycle_instance = None

            if bike_selection_type == 'existing':
                motorcycle_instance = form.cleaned_data.get('existing_motorcycle')
                 # No need to update existing motorcycle details from the form

            elif bike_selection_type == 'new':
                motorcycle_instance = CustomerMotorcycle(
                    owner=user,
                    make=form.cleaned_data['new_bike_make'],
                    model=form.cleaned_data['new_bike_model'],
                    year=form.cleaned_data['new_bike_year'],
                    rego=form.cleaned_data.get('new_bike_rego', ''),
                    vin_number=form.cleaned_data.get('new_bike_vin_number', ''),
                    odometer=form.cleaned_data.get('new_bike_odometer'),
                    transmission=form.cleaned_data.get('new_bike_transmission', ''),
                )
                motorcycle_instance.save()
                messages.success(request, f"New motorcycle added for {user.get_full_name() or user.username}.")

            # Create the ServiceBooking instance
            booking = ServiceBooking(
                customer=user,
                # Fetch current user details to store on the booking (using potentially updated details)
                customer_name=f"{user.first_name} {user.last_name}",
                customer_email=user.email,
                customer_phone=getattr(user, 'phone_number', ''), # Safely get phone_number
                # Note: Customer address is not captured in this flow, but could be added from user model
                vehicle=motorcycle_instance,
                service_type=service_type,
                appointment_datetime=appointment_datetime,
                preferred_contact=preferred_contact,
                customer_notes=booking_comments,
                status='pending', # Default status
            )
            booking.save()

            messages.success(request, f"Service booking created successfully for {user.get_full_name() or user.username}.")
            return redirect(reverse('service:admin_booking_user')) # Redirect back to this form or a success page

        else:
            # --- Debugging: Print form errors to the console ---
            print("Form is invalid. Errors:")
            print(form.errors)
            # --- End Debugging ---
            messages.error(request, "Please correct the errors below.")
            # If form is invalid, and a user was selected, pass the user instance
            # so the template can potentially re-display user details and motorcycles.
            # The user_instance variable already holds this if user_id was in POST.
            pass

    else: # GET request
        # Use the new form for existing user bookings
        form = AdminUserBookingForm()

    context = {
        'page_title': 'Admin Service Booking for Existing User',
        'form': form,
        'selected_user': user_instance, # Pass the user instance if available (e.g., after failed POST)
    }
    return render(request, 'service/service_booking_admin_user.html', context)

# --- AJAX Helper Views (Implemented) ---
@user_passes_test(is_staff_or_superuser)
@require_GET
def get_user_details_for_admin(request, user_id):
    """Returns JSON response with user details for admin booking form."""
    try:
        user = get_object_or_404(User, id=user_id)
        data = {
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'phone_number': getattr(user, 'phone_number', ''), # Safely get phone_number
            # Add other user fields here if needed, e.g., address
            # 'address_line_1': user.address_line_1,
            # 'city': user.city,
            # ...
        }
        return JsonResponse(data)
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except Exception as e:
        # Log the error or handle it as appropriate
        print(f"Error fetching user details: {e}") # Basic logging
        return JsonResponse({'error': 'Internal server error'}, status=500)


@user_passes_test(is_staff_or_superuser)
@require_GET
def get_user_motorcycles_for_admin(request, user_id):
    """Returns JSON response with user's motorcycles for admin booking form."""
    try:
        user = get_object_or_404(User, id=user_id)
        # Select specific fields to avoid sending unnecessary data
        motorcycles = CustomerMotorcycle.objects.filter(owner=user).values(
            'id', 'make', 'model', 'year', 'rego'
        ).order_by('year', 'make', 'model') # Order for better display
        data = {'motorcycles': list(motorcycles)}
        return JsonResponse(data)
    except User.DoesNotExist:
         return JsonResponse({'error': 'User not found'}, status=404)
    except Exception as e:
        # Log the error or handle it as appropriate
        print(f"Error fetching user motorcycles: {e}") # Basic logging
        return JsonResponse({'error': 'Internal server error'}, status=500)


@user_passes_test(is_staff_or_superuser)
@require_GET
def get_motorcycle_details_for_admin(request, motorcycle_id):
    """Returns JSON response with motorcycle details for admin booking form."""
    try:
        motorcycle = get_object_or_404(CustomerMotorcycle, id=motorcycle_id)
        data = {
            'make': motorcycle.make,
            'model': motorcycle.model,
            'year': motorcycle.year,
            'rego': motorcycle.rego,
            'vin_number': motorcycle.vin_number,
            'odometer': motorcycle.odometer,
            'transmission': motorcycle.transmission,
        }
        return JsonResponse(data)
    except CustomerMotorcycle.DoesNotExist:
        return JsonResponse({'error': 'Motorcycle not found'}, status=404)
    except Exception as e:
        # Log the error or handle it as appropriate
        print(f"Error fetching motorcycle details: {e}") # Basic logging
        return JsonResponse({'error': 'Internal server error'}, status=500)
