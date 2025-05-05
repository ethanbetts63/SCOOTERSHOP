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

# Handles the first step of booking: service type and appointment time.
def booking_step1(request):
    settings = SiteSettings.get_settings()
    if not settings.enable_service_booking:
        messages.error(request, "Service booking is currently disabled.")
        return redirect(reverse('core:index'))

    if not request.user.is_authenticated and not settings.allow_anonymous_bookings:
         messages.info(request, "Please log in or register to book a service.")
         return redirect(reverse('users:login'))

    booking_data = request.session.get(SERVICE_BOOKING_SESSION_KEY, {})

    if request.method == 'POST':
        form = ServiceDetailsForm(request.POST)
        if form.is_valid():
            # Create a new booking_data dictionary to start fresh
            booking_data = {}
            
            # Handle service_type field
            service_type_instance = form.cleaned_data.get('service_type')
            if service_type_instance:
                booking_data['service_type_id'] = service_type_instance.id
            else:
                 messages.error(request, "Invalid service type selected.")
                 context = {
                     'form': form,
                     'step': 1,
                     'total_steps': 3,
                     'is_authenticated': request.user.is_authenticated,
                     'allow_anonymous_bookings': settings.allow_anonymous_bookings,
                 }
                 return render(request, 'service/service_details.html', context)

            # Handle appointment_datetime field
            appointment_datetime = form.cleaned_data.get('appointment_datetime')
            if appointment_datetime and isinstance(appointment_datetime, datetime.datetime):
                booking_data['appointment_datetime_str'] = appointment_datetime.isoformat()
            else:
                 messages.error(request, "Invalid appointment date/time.")
                 context = {
                     'form': form,
                     'step': 1,
                     'total_steps': 3,
                     'is_authenticated': request.user.is_authenticated,
                     'allow_anonymous_bookings': settings.allow_anonymous_bookings,
                 }
                 return render(request, 'service/service_details.html', context)
            
            # Fix: Get booking_comments from form.cleaned_data instead of notes
            booking_comments = form.cleaned_data.get('booking_comments', '')
            booking_data['notes'] = booking_comments
                
            request.session[SERVICE_BOOKING_SESSION_KEY] = booking_data
            request.session.modified = True

            if request.user.is_authenticated:
                return redirect(reverse('service:service_step2_authenticated'))
            else:
                return redirect(reverse('service:service_step2_anonymous'))
        else:
            messages.error(request, "Please correct the errors below.")
            context = {
                'form': form,
                'step': 1,
                'total_steps': 3,
                'is_authenticated': request.user.is_authenticated,
                'allow_anonymous_bookings': settings.allow_anonymous_bookings,
            }
            return render(request, 'service/service_details.html', context)

    else:
        initial_data = booking_data.copy()

        if 'appointment_datetime_str' in initial_data:
             try:
                initial_data['appointment_datetime'] = datetime.datetime.fromisoformat(initial_data['appointment_datetime_str'])
             except (ValueError, TypeError):
                 pass

        service_type_id = initial_data.get('service_type_id')
        if service_type_id:
            try:
                service_type_instance = ServiceType.objects.get(id=service_type_id)
                initial_data['service_type'] = service_type_instance
            except ServiceType.DoesNotExist:
                pass

        # Fix: Map notes from session to booking_comments field in form
        if 'notes' in initial_data:
            initial_data['booking_comments'] = initial_data.pop('notes')

        form = ServiceDetailsForm(initial=initial_data)

    context = {
        'form': form,
        'step': 1,
        'total_steps': 3,
        'is_authenticated': request.user.is_authenticated,
        'allow_anonymous_bookings': settings.allow_anonymous_bookings,
    }
    return render(request, 'service/service_details.html', context)