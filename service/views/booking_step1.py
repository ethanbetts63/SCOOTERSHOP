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
    ServiceBookingUserForm, # Keep this imported in case it's used elsewhere in the file
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

    # Adjust min_booking_date to be at least tomorrow if advance notice is 0
    # Or ensure it's truly 'advance' notice days *from* today
    # Let's stick to the current interpretation for now as it matches the setting description
    # min_booking_date = today + timedelta(days=settings.booking_advance_notice)

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

    # Handle cases where start and end times are the same or invalid range
    if start_time >= end_time:
        return [] # No valid time range

    # Convert time objects to datetime objects for easy timedelta arithmetic
    # start_datetime_today = datetime.datetime.combine(today, start_time) # Not needed here
    # end_datetime_today = datetime.datetime.combine(today, end_time) # Not needed here

    # Combine selected_date with start and end times
    start_datetime_selected = datetime.datetime.combine(selected_date, start_time)
    end_datetime_selected = datetime.datetime.combine(selected_date, end_time)

    potential_slots = []
    current_time_dt = start_datetime_selected
    while current_time_dt <= end_datetime_selected:
        potential_slots.append(current_time_dt.time())
        current_time_dt += timedelta(minutes=booking_interval_minutes)

    # 4. Check existing bookings to determine availability for each slot
    # IMPORTANT: Capacity logic is simplified here (1 booking per 15-min slot).
    # You may need a more sophisticated approach for capacity management.
    booked_slots_count = {}
    # Filter bookings for the selected date
    bookings_on_date = ServiceBooking.objects.filter(appointment_date=selected_date)

    for booking in bookings_on_date:
        slot_time = booking.drop_off_time
        # We need to count bookings per exact time slot available in potential_slots.
        # A simple way is to convert the booked time to a string 'HH:MM' which matches
        # the format used for slot values.
        slot_time_str = slot_time.strftime('%H:%M')
        booked_slots_count[slot_time_str] = booked_slots_count.get(slot_time_str, 0) + 1


    # Determine which slots are available based on a simplified capacity
    # Assume max 1 booking per 15-minute slot for now
    max_bookings_per_slot = 1 # This should ideally be a setting

    available_slots_list = []
    for slot_time in potential_slots:
        slot_time_str = slot_time.strftime('%H:%M')
        bookings_at_slot = booked_slots_count.get(slot_time_str, 0)
        if bookings_at_slot < max_bookings_per_slot:
            # Format time for the form choice field (e.g., "09:00", "9:00 AM")
             # Use %I:%M %p for 12-hour format with AM/PM, %H:%M for 24-hour value
            available_slots_list.append((slot_time_str, slot_time.strftime('%I:%M %p').lstrip('0'))) # (value, display_text)

    # 5. Ensure at least one slot is free (Condition 2) - This filtering is handled
    # by returning only available slots. If the list is empty, no slots are free.

    return available_slots_list

# AJAX endpoint to get available time slots for a specific date
def get_available_slots_ajax(request):
    """
    View to return available time slots for a given date via AJAX.
    """
    selected_date_str = request.GET.get('date')
    if not selected_date_str:
        return JsonResponse({'error': 'Date parameter is missing'}, status=400)

    try:
        # Parse the date string in the expected Y-m-d format
        selected_date = datetime.datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Invalid date format. Use<\ctrl97>-MM-DD'}, status=400)

    available_slots = get_available_time_slots(selected_date)

    # Format slots for JSON response as a list of {value: 'HH:MM', text: 'HH:MM AM/PM'}
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
        # Instantiate the form with POST data
        form = ServiceDetailsForm(request.POST)

        # --- Important Fix: Populate time choices before validating on POST ---
        # Get the selected date from the POST data
        selected_date_str_from_post = request.POST.get('appointment_date')
        available_time_slots_for_form = [] # List of (value, text) tuples for form choices
        available_time_slots_json_for_template = [] # Initialize for template context

        if selected_date_str_from_post:
            try:
                # Parse the date string
                selected_date_from_post = datetime.datetime.strptime(selected_date_str_from_post, '%Y-%m-%d').date()
                # Get available time slots for this date
                available_time_slots_for_form = get_available_time_slots(selected_date_from_post)
                # Populate the choices for the drop_off_time field in the form instance
                form.fields['drop_off_time'].choices = available_time_slots_for_form
                 # Also format for the frontend JS if date was valid
                available_time_slots_json_for_template = [{'value': slot[0], 'text': slot[1]} for slot in available_time_slots_for_form]

            except ValueError:
                # If the date format is invalid, the form will handle it,
                # but we won't be able to populate time slots dynamically here.
                # available_time_slots_for_form and available_time_slots_json_for_template remain []
                pass # Let form validation handle the date error

        # --- End Fix ---

        if form.is_valid():
            # Create a new booking_data dictionary to start fresh
            booking_data = {}

            # Handle service_type field
            service_type_instance = form.cleaned_data.get('service_type')
            # This check is still valid
            if service_type_instance:
                booking_data['service_type_id'] = service_type_instance.id
            else:
                 # This case should ideally be caught by form validation if service_type is required
                 messages.error(request, "Invalid service type selected.")
                 context = {
                     'form': form, # Form already has choices populated if date was valid
                     'step': 1,
                     'total_steps': 3,
                     'is_authenticated': request.user.is_authenticated,
                     'allow_anonymous_bookings': settings.allow_anonymous_bookings,
                     # Pass available time slots to template if form is invalid on POST
                     'available_time_slots_json': json.dumps(available_time_slots_json_for_template) # Use the variable here
                 }
                 return render(request, 'service/service_details.html', context)


            # Handle appointment_date and drop_off_time fields separately
            appointment_date = form.cleaned_data.get('appointment_date')
            drop_off_time_str = form.cleaned_data.get('drop_off_time') # This will be a string like 'HH:MM'

            # These checks are still valid after populating choices
            if appointment_date and drop_off_time_str:
                 # Store the date and time as separate items
                 booking_data['appointment_date_str'] = appointment_date.isoformat()
                 booking_data['drop_off_time_str'] = drop_off_time_str # Store as string 'HH:MM'
            else:
                 # This case should ideally be caught by form validation
                 messages.error(request, "Invalid appointment date or time.")
                 # On error, re-render the form with the choices populated
                 context = {
                     'form': form, # Form already has choices populated if date was valid
                     'step': 1,
                     'total_steps': 3,
                     'is_authenticated': request.user.is_authenticated,
                     'allow_anonymous_bookings': settings.allow_anonymous_bookings,
                     'available_time_slots_json': json.dumps(available_time_slots_json_for_template) # Use the variable here
                 }
                 return render(request, 'service/service_details.html', context)

            # Removed handling of booking_comments from POST

            request.session[SERVICE_BOOKING_SESSION_KEY] = booking_data
            request.session.modified = True

            # Redirect to the next step
            if request.user.is_authenticated:
                return redirect(reverse('service:service_step2_authenticated'))
            else:
                return redirect(reverse('service:service_step2_anonymous'))

        else: # Form is not valid on POST
            messages.error(request, "Please correct the errors below.")
            # The form instance 'form' already has its drop_off_time choices populated
            # by the logic added before form.is_valid().
            # available_time_slots_json_for_template was also populated if date was valid.

            context = {
                'form': form, # Pass the form instance with populated choices and errors
                'step': 1,
                'total_steps': 3,
                'is_authenticated': request.user.is_authenticated,
                'allow_anonymous_bookings': settings.allow_anonymous_bookings,
                 # Pass available time slots to template if form is invalid on POST
                 'available_time_slots_json': json.dumps(available_time_slots_json_for_template) # Use the variable here
            }
            return render(request, 'service/service_details.html', context)

    else: # GET request
        initial_data = booking_data.copy()

        # Instantiate the form for GET request
        form = ServiceDetailsForm(initial=initial_data)
        available_time_slots_for_form = [] # List of (value, text) tuples for form choices
        available_time_slots_json_for_template = [] # Initialize for template context

        # On GET, if a date was previously selected (e.g., returning to this step),
        # populate the time slots for that date.
        appointment_date_str = initial_data.get('appointment_date_str')
        if appointment_date_str:
             try:
                appointment_date = datetime.datetime.fromisoformat(appointment_date_str).date()
                available_time_slots_for_form = get_available_time_slots(appointment_date)
                # Populate time choices for the form
                form.fields['drop_off_time'].choices = available_time_slots_for_form
                # Set the initial value for drop_off_time if it exists in session
                initial_drop_off_time = initial_data.get('drop_off_time_str')
                # Only set initial value if it's one of the available choices
                if initial_drop_off_time and any(slot[0] == initial_drop_off_time for slot in available_time_slots_for_form):
                     form.initial['drop_off_time'] = initial_drop_off_time
                else:
                     # If the stored time is no longer available, clear it from initial data
                     form.initial.pop('drop_off_time', None)

                 # Also format for the frontend JS if date was in session
                available_time_slots_json_for_template = [{'value': slot[0], 'text': slot[1]} for slot in available_time_slots_for_form]

             except (ValueError, TypeError):
                 # Handle cases where session data is invalid
                 # available_time_slots_json_for_template remains [] due to initial assignment
                 pass

        # Removed handling of 'notes' from session for form initialization

    # Pass necessary data to the template for Flatpickr configuration and initial time slot population
    # This is outside the if appointment_date_str: block
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
        # Pass initial available slots to template for frontend JS to populate
        'available_time_slots_json': json.dumps(available_time_slots_json_for_template) # Use the variable here
    }
    return render(request, 'service/service_details.html', context)