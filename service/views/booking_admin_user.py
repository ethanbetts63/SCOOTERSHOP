# service/views/booking_admin_user.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.urls import reverse
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from service.forms import AdminUserBookingForm
from service.models import ServiceBooking, CustomerMotorcycle, ServiceType
from users.models import User

# Checks if the user is staff or a superuser
def is_staff_or_superuser(user):
    return user.is_active and (user.is_staff or user.is_superuser)

# Handles admin booking for existing users
@user_passes_test(is_staff_or_superuser)
def booking_admin_user_view(request):
    user_id = request.POST.get('user') if request.method == 'POST' else None
    user_instance = None
    if user_id:
        try:
            # Gets user instance by ID
            user_instance = User.objects.get(id=user_id)
        except User.DoesNotExist:
            pass

    if request.method == 'POST':
        # Initializes form with POST data
        form = AdminUserBookingForm(request.POST)
        if user_instance:
             # Filters motorcycles based on user
             form.fields['existing_motorcycle'].queryset = CustomerMotorcycle.objects.filter(owner=user_instance).order_by('make', 'model')

        if form.is_valid():
            # Gets user from cleaned form data
            user = form.cleaned_data.get('user')

            # Updates user details if provided
            user_to_update = get_object_or_404(User, id=user.id)
            if form.cleaned_data.get('user_first_name'):
                user_to_update.first_name = form.cleaned_data['user_first_name']
            if form.cleaned_data.get('user_last_name'):
                user_to_update.last_name = form.cleaned_data['user_last_name']
            if form.cleaned_data.get('user_email'):
                user_to_update.email = form.cleaned_data['user_email']
            if form.cleaned_data.get('user_phone_number'):
                 setattr(user_to_update, 'phone_number', form.cleaned_data['user_phone_number'])

            # Saves the updated user
            user_to_update.save()
            # Displays success message for user update
            messages.success(request, f"User details updated for {user_to_update.get_full_name() or user_to_update.username}.")

            # Extracts booking details from form
            bike_selection_type = form.cleaned_data['bike_selection_type']
            service_type = form.cleaned_data['service_type']
            appointment_datetime = form.cleaned_data['appointment_datetime']
            preferred_contact = form.cleaned_data['preferred_contact']
            booking_comments = form.cleaned_data.get('booking_comments', '')

            motorcycle_instance = None

            # Handles existing motorcycle selection
            if bike_selection_type == 'existing':
                motorcycle_instance = form.cleaned_data.get('existing_motorcycle')

            # Handles new motorcycle creation
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
                # Saves the new motorcycle
                motorcycle_instance.save()
                # Displays success message for new motorcycle
                messages.success(request, f"New motorcycle added for {user.get_full_name() or user.username}.")

            # Creates a new ServiceBooking instance
            booking = ServiceBooking(
                customer=user,
                customer_name=f"{user.first_name} {user.last_name}",
                customer_email=user.email,
                customer_phone=getattr(user, 'phone_number', ''),
                vehicle=motorcycle_instance,
                service_type=service_type,
                appointment_datetime=appointment_datetime,
                preferred_contact=preferred_contact,
                customer_notes=booking_comments,
                status='pending',
            )
            # Saves the booking to the database
            booking.save()

            # Displays success message for booking
            messages.success(request, f"Service booking created successfully for {user.get_full_name() or user.username}.")
            # Redirects to the same view
            return redirect(reverse('service:admin_booking_user'))

        else:
            # Displays error message for invalid form
            print("Form is invalid. Errors:")
            print(form.errors)
            messages.error(request, "Please correct the errors below.")

    else:
        # Initializes an empty form for GET requests
        form = AdminUserBookingForm()

    # Prepares context for rendering the template
    context = {
        'page_title': 'Admin Service Booking for Existing User',
        'form': form,
        'selected_user': user_instance,
    }
    # Renders the booking template
    return render(request, 'service/service_booking_admin_user.html', context)

# Returns JSON response with user details
@user_passes_test(is_staff_or_superuser)
@require_GET
def get_user_details_for_admin(request, user_id):
    try:
        # Gets user instance by ID
        user = get_object_or_404(User, id=user_id)
        # Prepares user data for JSON response
        data = {
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'phone_number': getattr(user, 'phone_number', ''),
        }
        # Returns JSON response
        return JsonResponse(data)
    except User.DoesNotExist:
        # Returns 404 if user not found
        return JsonResponse({'error': 'User not found'}, status=404)
    except Exception as e:
        # Prints error for debugging
        print(f"Error fetching user details: {e}")
        # Returns 500 for internal server error
        return JsonResponse({'error': 'Internal server error'}, status=500)

# Returns JSON response with user's motorcycles
@user_passes_test(is_staff_or_superuser)
@require_GET
def get_user_motorcycles_for_admin(request, user_id):
    try:
        # Gets user instance by ID
        user = get_object_or_404(User, id=user_id)
        # Filters and orders user's motorcycles
        motorcycles = CustomerMotorcycle.objects.filter(owner=user).values(
            'id', 'make', 'model', 'year', 'rego'
        ).order_by('year', 'make', 'model')
        # Prepares motorcycle data for JSON response
        data = {'motorcycles': list(motorcycles)}
        # Returns JSON response
        return JsonResponse(data)
    except User.DoesNotExist:
         # Returns 404 if user not found
         return JsonResponse({'error': 'User not found'}, status=404)
    except Exception as e:
        # Prints error for debugging
        print(f"Error fetching user motorcycles: {e}")
        # Returns 500 for internal server error
        return JsonResponse({'error': 'Internal server error'}, status=500)

# Returns JSON response with motorcycle details
@user_passes_test(is_staff_or_superuser)
@require_GET
def get_motorcycle_details_for_admin(request, motorcycle_id):
    try:
        # Gets motorcycle instance by ID
        motorcycle = get_object_or_404(CustomerMotorcycle, id=motorcycle_id)
        # Prepares motorcycle data for JSON response
        data = {
            'make': motorcycle.make,
            'model': motorcycle.model,
            'year': motorcycle.year,
            'rego': motorcycle.rego,
            'vin_number': motorcycle.vin_number,
            'odometer': motorcycle.odometer,
            'transmission': motorcycle.transmission,
        }
        # Returns JSON response
        return JsonResponse(data)
    except CustomerMotorcycle.DoesNotExist:
        # Returns 404 if motorcycle not found
        return JsonResponse({'error': 'Motorcycle not found'}, status=404)
    except Exception as e:
        # Prints error for debugging
        print(f"Error fetching motorcycle details: {e}")
        # Returns 500 for internal server error
        return JsonResponse({'error': 'Internal server error'}, status=500)