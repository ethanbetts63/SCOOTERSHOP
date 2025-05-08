from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
import datetime
from django.db.models import Q
from service.models import ServiceBooking, CustomerMotorcycle, ServiceType
from dashboard.models import SiteSettings, BlockedDate # Import BlockedDate
from service.forms import (
    ServiceDetailsForm,
    CustomerMotorcycleForm,
    ServiceBookingUserForm,
    ExistingCustomerMotorcycleForm,
)
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta, time
import json # Needed for potential AJAX response
from django.http import JsonResponse # Needed for AJAX response

SERVICE_BOOKING_SESSION_KEY = 'service_booking_data'

# Helper function to calculate available time slots for a given date
def get_available_time_slots(selected_date):
    """
    Calculates available 15-minute time slots for a given date
    based on site settings, blocked dates, and existing bookings.
    """
    settings = SiteSettings.get_settings()
    available_slots = []
    booking_interval_minutes = 15 # Define the booking interval

    # 1. Check if the date is within the allowed booking window
    today = timezone.now().date()
    min_booking_date = today + timedelta(days=settings.booking_advance_notice)
    max_booking_date = today + timedelta(days=settings.booking_open_days)

    if not (min_booking_date <= selected_date <= max_booking_date):
        # Date is outside the allowed range
        return []

    # 2. Check if the date is blocked
    is_blocked = BlockedDate.objects.filter(
        start_date__lte=selected_date,
        end_date__gte=selected_date
    ).exists()

    if is_blocked:
        return []

    # 3. Generate potential time slots for the day
    start_time = settings.drop_off_start_time
    end_time = settings.drop_off_end_time

    current_time = datetime.datetime.combine(selected_date, start_time)
    end_datetime = datetime.datetime.combine(selected_date, end_time)

    potential_slots = []
    while current_time <= end_datetime:
        potential_slots.append(current_time.time())
        current_time += timedelta(minutes=booking_interval_minutes)

    # 4. Check existing bookings to determine availability for each slot
    # IMPORTANT: Capacity logic is simplified here (1 booking per 15-min slot).
    # You may need a more sophisticated approach for capacity management.
    booked_slots_count = {}
    bookings_on_date = ServiceBooking.objects.filter(appointment_date=selected_date)

    for booking in bookings_on_date:
        slot_time = booking.drop_off_time
        # Round the booked time to the nearest booking interval for counting
        # This is a basic approach; more complex logic might be needed if bookings aren't exactly on interval
        slot_dt = datetime.datetime.combine(selected_date, slot_time)
        rounded_slot_dt = datetime.datetime.combine(selected_date, start_time)
        while rounded_slot_dt <= slot_dt:
            if abs((slot_dt - rounded_slot_dt).total_seconds()) < (booking_interval_minutes * 60) / 2: # Check if within half interval
                 slot_time_rounded = rounded_slot_dt.time()
                 booked_slots_count[slot_time_rounded] = booked_slots_count.get(slot_time_rounded, 0) + 1
                 break # Found the interval, move to next booking
            rounded_slot_dt += timedelta(minutes=booking_interval_minutes)


    # Determine which slots are available based on a simplified capacity
    # Assume max 1 booking per 15-minute slot for now
    max_bookings_per_slot = 1 # This should ideally be a setting

    for slot_time in potential_slots:
        bookings_at_slot = booked_slots_count.get(slot_time, 0)
        if bookings_at_slot < max_bookings_per_slot:
            # Format time for the form choice field (e.g., "09:00")
            available_slots.append((slot_time.strftime('%H:%M'), slot_time.strftime('%I:%M %p'))) # (value, display_text)

    # 5. Ensure at least one slot is free (Condition 2) - This filtering is handled
    # by returning only available slots. If the list is empty, no slots are free.

    return available_slots

# AJAX endpoint to get available time slots for a specific date
def get_available_slots_ajax(request):
    """
    View to return available time slots for a given date via AJAX.
    """
    selected_date_str = request.GET.get('date')
    if not selected_date_str:
        return JsonResponse({'error': 'Date parameter is missing'}, status=400)

    try:
        selected_date = datetime.datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)

    available_slots = get_available_time_slots(selected_date)

    # Format slots for JSON response
    formatted_slots = [{'value': slot[0], 'text': slot[1]} for slot in available_slots]

    return JsonResponse({'available_slots': formatted_slots})


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
                 # Re-populate form with errors and available slots for the date the user tried to book
                 # This requires getting the selected date from POST data
                 selected_date_str_from_post = request.POST.get('appointment_date')
                 available_time_slots = []
                 if selected_date_str_from_post:
                     try:
                         selected_date_from_post = datetime.datetime.strptime(selected_date_str_from_post, '%Y-%m-%d').date()
                         available_time_slots = get_available_time_slots(selected_date_from_post)
                         form.fields['drop_off_time'].choices = available_time_slots # Populate time choices
                     except ValueError:
                         pass # Handle invalid date format from POST if necessary

                 context = {
                     'form': form,
                     'step': 1,
                     'total_steps': 3,
                     'is_authenticated': request.user.is_authenticated,
                     'allow_anonymous_bookings': settings.allow_anonymous_bookings,
                     'available_time_slots_json': json.dumps(available_time_slots) # Pass to template for re-rendering
                 }
                 return render(request, 'service/service_details.html', context)


            # Handle appointment_date and drop_off_time fields separately
            appointment_date = form.cleaned_data.get('appointment_date')
            drop_off_time = form.cleaned_data.get('drop_off_time') # This will be a string like '09:00'

            if appointment_date and drop_off_time:
                 # Store the date and time as separate items
                 booking_data['appointment_date_str'] = appointment_date.isoformat()
                 booking_data['drop_off_time_str'] = drop_off_time # Store as string 'HH:MM'
            else:
                 messages.error(request, "Invalid appointment date or time.")
                 # Re-populate form with errors and available slots
                 selected_date_str_from_post = request.POST.get('appointment_date')
                 available_time_slots = []
                 if selected_date_str_from_post:
                     try:
                         selected_date_from_post = datetime.datetime.strptime(selected_date_str_from_post, '%Y-%m-%d').date()
                         available_time_slots = get_available_time_slots(selected_date_from_post)
                         form.fields['drop_off_time'].choices = available_time_slots # Populate time choices
                     except ValueError:
                         pass

                 context = {
                     'form': form,
                     'step': 1,
                     'total_steps': 3,
                     'is_authenticated': request.user.is_authenticated,
                     'allow_anonymous_bookings': settings.allow_anonymous_bookings,
                     'available_time_slots_json': json.dumps(available_time_slots)
                 }
                 return render(request, 'service/service_details.html', context)


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
            # If form is invalid, attempt to repopulate time slots based on the date submitted
            selected_date_str_from_post = request.POST.get('appointment_date')
            available_time_slots = []
            if selected_date_str_from_post:
                 try:
                     selected_date_from_post = datetime.datetime.strptime(selected_date_str_from_post, '%Y-%m-%d').date()
                     available_time_slots = get_available_time_slots(selected_date_from_post)
                     form.fields['drop_off_time'].choices = available_time_slots # Populate time choices
                 except ValueError:
                     pass # Handle invalid date format from POST if necessary


            context = {
                'form': form,
                'step': 1,
                'total_steps': 3,
                'is_authenticated': request.user.is_authenticated,
                'allow_anonymous_bookings': settings.allow_anonymous_bookings,
                 'available_time_slots_json': json.dumps(available_time_slots) # Pass to template
            }
            return render(request, 'service/service_details.html', context)

    else: # GET request
        initial_data = booking_data.copy()

        form = ServiceDetailsForm(initial=initial_data)
        available_time_slots = []

        # On GET, if a date was previously selected (e.g., returning to this step),
        # populate the time slots for that date.
        appointment_date_str = initial_data.get('appointment_date_str')
        if appointment_date_str:
             try:
                appointment_date = datetime.datetime.fromisoformat(appointment_date_str).date()
                available_time_slots = get_available_time_slots(appointment_date)
                form.fields['drop_off_time'].choices = available_time_slots # Populate time choices
                # Set the initial value for drop_off_time if it exists in session
                initial_drop_off_time = initial_data.get('drop_off_time_str')
                if initial_drop_off_time and (initial_drop_off_time, initial_drop_off_time) in available_time_slots:
                     form.initial['drop_off_time'] = initial_drop_off_time

             except (ValueError, TypeError):
                 pass # Handle cases where session data is invalid

        # Fix: Map notes from session to booking_comments field in form
        if 'notes' in initial_data:
            initial_data['booking_comments'] = initial_data.pop('notes')


    # Pass necessary data to the template for Flatpickr configuration
    settings = SiteSettings.get_settings()
    blocked_dates = BlockedDate.objects.all()
    blocked_date_ranges = []
    for blocked in blocked_dates:
         blocked_date_ranges.append({
             'from': blocked.start_date.strftime('%Y-%m-%d'),
             'to': blocked.end_date.strftime('%Y-%m-%d')
         })

    # Calculate min and max dates allowed by booking_advance_notice and booking_open_days
    today = timezone.now().date()
    min_date = today + timedelta(days=settings.booking_advance_notice)
    max_date = today + timedelta(days=settings.booking_open_days)


    context = {
        'form': form,
        'step': 1,
        'total_steps': 3,
        'is_authenticated': request.user.is_authenticated,
        'allow_anonymous_bookings': settings.allow_anonymous_bookings,
        'blocked_date_ranges_json': json.dumps(blocked_date_ranges), # Pass blocked dates to template
        'min_date': min_date.strftime('%Y-%m-%d'), # Pass min date to template
        'max_date': max_date.strftime('%Y-%m-%d'), # Pass max date to template
        'available_time_slots_json': json.dumps(available_time_slots) # Pass initial available slots (if date in session)
    }
    return render(request, 'service/service_details.html', context)