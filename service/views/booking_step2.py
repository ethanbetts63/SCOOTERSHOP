from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
import datetime
from django.db.models import Q
from service.models import ServiceBooking, CustomerMotorcycle, ServiceType
from dashboard.models import SiteSettings
from service.forms import (
    ServiceDetailsForm,
    CustomerMotorcycleForm,
    ServiceBookingUserForm,
    ExistingCustomerMotorcycleForm,
)
from django.contrib.auth.decorators import login_required
from django.utils import timezone

SERVICE_BOOKING_SESSION_KEY = 'service_booking_data'

# Handles the second step of booking for authenticated users: vehicle details.
@login_required
def booking_step2_authenticated(request):
    settings = SiteSettings.get_settings()
    if not settings.enable_service_booking:
        messages.error(request, "Service booking is currently disabled.")
        return redirect(reverse('core:index'))

    booking_data = request.session.get(SERVICE_BOOKING_SESSION_KEY)
    if not booking_data:
        messages.warning(request, "Please start the booking process again.")
        return redirect(reverse('service:service_step1'))

    user = request.user
    user_motorcycles = CustomerMotorcycle.objects.filter(owner=user)
    has_existing_bikes = user_motorcycles.exists()

    existing_bike_form = None
    motorcycle_form = None
    selected_motorcycle = None

    display_existing_selection = True
    display_motorcycle_details = False
    editing_motorcycle = None

    if request.method == 'GET':
        if has_existing_bikes:
            existing_bike_form = ExistingCustomerMotorcycleForm(user=user)
            motorcycle_form = CustomerMotorcycleForm()
            display_existing_selection = True
            display_motorcycle_details = False

            booking_data.pop('vehicle_id', None)
            booking_data['edit_motorcycle_mode'] = False
            request.session[SERVICE_BOOKING_SESSION_KEY] = booking_data
            request.session.modified = True

        else:
            motorcycle_form = CustomerMotorcycleForm()
            display_existing_selection = False
            display_motorcycle_details = True
            messages.info(request, "Please provide details for your motorcycle.")
            booking_data['edit_motorcycle_mode'] = False
            booking_data.pop('vehicle_id', None)
            request.session[SERVICE_BOOKING_SESSION_KEY] = booking_data
            request.session.modified = True

    elif request.method == 'POST':
        action = request.POST.get('action')

        if action == 'select_existing' and has_existing_bikes:
            existing_bike_form = ExistingCustomerMotorcycleForm(request.POST, user=user)
            if existing_bike_form.is_valid():
                selected_motorcycle = existing_bike_form.cleaned_data['motorcycle']
                booking_data['vehicle_id'] = selected_motorcycle.id
                booking_data['edit_motorcycle_mode'] = True
                request.session[SERVICE_BOOKING_SESSION_KEY] = booking_data
                request.session.modified = True

                motorcycle_form = CustomerMotorcycleForm(instance=selected_motorcycle)
                editing_motorcycle = selected_motorcycle
                display_existing_selection = False
                display_motorcycle_details = True
                messages.info(request, f"Details for {selected_motorcycle} loaded. Please confirm or update them if needed.")
            else:
                messages.error(request, "Please select a valid existing motorcycle.")
                display_existing_selection = True
                display_motorcycle_details = False
                existing_bike_form = ExistingCustomerMotorcycleForm(request.POST, user=user)
                motorcycle_form = CustomerMotorcycleForm()

        elif action == 'add_new':
            motorcycle_form = CustomerMotorcycleForm(request.POST)
            display_existing_selection = False
            display_motorcycle_details = True

            booking_data['edit_motorcycle_mode'] = False
            booking_data.pop('vehicle_id', None)
            request.session[SERVICE_BOOKING_SESSION_KEY] = booking_data
            request.session.modified = True

            if motorcycle_form.is_valid():
                new_motorcycle = motorcycle_form.save(commit=False)
                new_motorcycle.owner = user
                new_motorcycle.save()

                booking_data['vehicle_id'] = new_motorcycle.id
                booking_data['edit_motorcycle_mode'] = True
                for key in ['anon_vehicle_make', 'anon_vehicle_model', 'anon_vehicle_year',
                           'anon_vehicle_rego', 'anon_vehicle_vin_number',
                           'anon_vehicle_odometer', 'anon_vehicle_transmission']:
                    booking_data.pop(key, None)

                request.session[SERVICE_BOOKING_SESSION_KEY] = booking_data
                request.session.modified = True
                messages.success(request, "New motorcycle added successfully.")
                return redirect(reverse('service:service_step3_authenticated'))
            else:
                messages.error(request, "Please correct the errors in the new motorcycle details.")
                if has_existing_bikes:
                    existing_bike_form = ExistingCustomerMotorcycleForm(user=user)
                    motorcycle_form = CustomerMotorcycleForm()

        elif action == 'edit_existing':
            vehicle_id_to_edit = booking_data.get('vehicle_id')
            if not vehicle_id_to_edit:
                messages.error(request, "No motorcycle selected for editing.")
                return redirect(reverse('service:service_step2_authenticated'))

            try:
                selected_motorcycle = CustomerMotorcycle.objects.get(id=vehicle_id_to_edit, owner=user)
                motorcycle_form = CustomerMotorcycleForm(request.POST, instance=selected_motorcycle)
                editing_motorcycle = selected_motorcycle
                display_existing_selection = False
                display_motorcycle_details = True

                booking_data['edit_motorcycle_mode'] = True
                request.session[SERVICE_BOOKING_SESSION_KEY] = booking_data
                request.session.modified = True

                if motorcycle_form.is_valid():
                    motorcycle_form.save()
                    messages.success(request, "Motorcycle details updated successfully.")
                    return redirect(reverse('service:service_step3_authenticated'))
                else:
                    messages.error(request, "Please correct the errors in the motorcycle details.")
                    if has_existing_bikes:
                        existing_bike_form = ExistingCustomerMotorcycleForm(
                            user=user,
                            initial={'motorcycle': selected_motorcycle}
                        )
            except CustomerMotorcycle.DoesNotExist:
                messages.error(request, "Motorcycle not found for editing.")
                booking_data.pop('vehicle_id', None)
                booking_data['edit_motorcycle_mode'] = False
                request.session[SERVICE_BOOKING_SESSION_KEY] = booking_data
                request.session.modified = True
                return redirect(reverse('service:service_step2_authenticated'))
        else:
            messages.error(request, "Invalid request.")
            if has_existing_bikes:
                 existing_bike_form = ExistingCustomerMotorcycleForm(user=user)
                 motorcycle_form = CustomerMotorcycleForm()
                 display_existing_selection = True
                 display_motorcycle_details = False
            else:
                 motorcycle_form = CustomerMotorcycleForm()
                 display_existing_selection = False
                 display_motorcycle_details = True
                 messages.info(request, "Please provide details for your motorcycle.")

    context = {
        'existing_bike_form': existing_bike_form,
        'motorcycle_form': motorcycle_form,
        'step': 2,
        'total_steps': 3,
        'is_authenticated': True,
        'has_existing_bikes': has_existing_bikes,
        'display_existing_selection': display_existing_selection,
        'display_motorcycle_details': display_motorcycle_details,
        'editing_motorcycle': editing_motorcycle,
        'edit_mode': booking_data.get('edit_motorcycle_mode', False)
    }
    return render(request, 'service/service_bike_details_authenticated.html', context)

# Handles the second step of booking for anonymous users: vehicle details.
def booking_step2_anonymous(request):
    settings = SiteSettings.get_settings()
    if not settings.enable_service_booking:
        messages.error(request, "Service booking is currently disabled.")
        return redirect(reverse('core:index'))
    if not settings.allow_anonymous_bookings:
         messages.error(request, "Anonymous bookings are not allowed.")
         return redirect(reverse('service:service_start'))

    booking_data = request.session.get(SERVICE_BOOKING_SESSION_KEY)
    if not booking_data:
        messages.warning(request, "Please start the booking process again.")
        return redirect(reverse('service:service_step1'))

    if request.method == 'POST':
        form = CustomerMotorcycleForm(request.POST)
        if form.is_valid():
            booking_data['anon_vehicle_make'] = form.cleaned_data['make']
            booking_data['anon_vehicle_model'] = form.cleaned_data['model']
            booking_data['anon_vehicle_year'] = form.cleaned_data['year']
            booking_data['anon_vehicle_rego'] = form.cleaned_data.get('rego')
            booking_data['anon_vehicle_vin_number'] = form.cleaned_data.get('vin_number')
            booking_data['anon_vehicle_odometer'] = form.cleaned_data.get('odometer')
            booking_data['anon_vehicle_transmission'] = form.cleaned_data.get('transmission')

            booking_data.pop('vehicle_id', None)
            booking_data['edit_motorcycle_mode'] = False

            request.session[SERVICE_BOOKING_SESSION_KEY] = booking_data
            request.session.modified = True
            return redirect(reverse('service:service_step3_anonymous'))
        else:
            messages.error(request, "Please correct the errors in the vehicle details.")
            context = {
                'form': form,
                'step': 2,
                'total_steps': 3,
                'is_authenticated': False,
                'allow_anonymous_bookings': settings.allow_anonymous_bookings,
            }
            return render(request, 'service/service_bike_details_anonymous.html', context)

    else:
        initial_data = {
            'make': booking_data.get('anon_vehicle_make'),
            'model': booking_data.get('anon_vehicle_model'),
            'year': booking_data.get('anon_vehicle_year'),
            'rego': booking_data.get('anon_vehicle_rego'),
            'vin_number': booking_data.get('anon_vehicle_vin_number'),
            'odometer': booking_data.get('anon_vehicle_odometer'),
            'transmission': booking_data.get('anon_vehicle_transmission'),
        }
        form = CustomerMotorcycleForm(initial=initial_data)
        context = {
            'form': form,
            'step': 2,
            'total_steps': 3,
            'is_authenticated': False,
            'allow_anonymous_bookings': settings.allow_anonymous_bookings,
        }

    return render(request, 'service/service_bike_details_anonymous.html', context)
