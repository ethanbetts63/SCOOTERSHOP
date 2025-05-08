from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
import datetime
from django.db.models import Q, Count # Import Count for aggregation
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

# Helper function to get dates disabled due to daily capacity limit
def get_disabled_dates_by_capacity():
    """
    Calculates dates that should be disabled because the total number of
    bookings on that day meets or exceeds max_visible_slots_per_day.
    Returns a list of date strings ('YYYY-MM-DD').
    """
    settings = SiteSettings.get_settings()
    disabled_dates = []

    # Daily capacity limit is only active if max_visible_slots_per_day is set and positive
    if settings.max_visible_slots_per_day is None or settings.max_visible_slots_per_day <= 0:
        return []

    # Calculate the date range to check based on booking_advance_notice and booking_open_days
    today = timezone.now().date()
    min_date = today + timedelta(days=settings.booking_advance_notice)
    max_date = today + timedelta(days=settings.booking_open_days)

    # Get booking counts for all dates within the relevant range
    booking_counts = ServiceBooking.objects.filter(
        appointment_date__gte=min_date,
        appointment_date__lte=max_date
    ).values('appointment_date').annotate(count=Count('id'))

    # Identify dates where the count meets or exceeds the daily limit
    for entry in booking_counts:
        if entry['count'] >= settings.max_visible_slots_per_day:
            disabled_dates.append(entry['appointment_date'].strftime('%Y-%m-%d'))

    return disabled_dates


# Helper function to generate all potential time slots for a given date
def generate_potential_time_slots(selected_date):
    """
    Generates all possible 15-minute time slots for a given date
    based on the drop-off start and end times from site settings.
    Does NOT check for existing bookings or capacity.
    Returns a list of (value, display_text) tuples.
    """
    settings = SiteSettings.get_settings()
    potential_slots_list = []
    booking_interval_minutes = 15 # Define the booking interval

    start_time = settings.drop_off_start_time
    end_time = settings.drop_off_end_time # Corrected field name

    # Handle cases where start and end times are the same or invalid range
    if start_time >= end_time:
        return [] # No valid time range

    # Combine selected_date with start and end times
    start_datetime_selected = datetime.datetime.combine(selected_date, start_time)
    end_datetime_selected = datetime.datetime.combine(selected_date, end_time)

    current_time_dt = start_datetime_selected
    while current_time_dt <= end_datetime_selected:
        # Format time for the form choice field (e.g., "09:00", "9:00 AM")
        # Use %I:%M %p for 12-hour format with AM/PM, %H:%M for 24-hour value
        potential_slots_list.append((current_time_dt.strftime('%H:%M'), current_time_dt.strftime('%I:%M %p').lstrip('0')))
        current_time_dt += timedelta(minutes=booking_interval_minutes)

    return potential_slots_list


# AJAX endpoint to get available time slots for a specific date
def get_available_slots_ajax(request):
    """
    View to return available time slots (all potential slots) for a given date via AJAX.
    This is called *after* the date has been selected and validated by the date picker.
    Per-time-slot capacity is ignored as per new requirement.
    """
    selected_date_str = request.GET.get('date')
    if not selected_date_str:
        return JsonResponse({'error': 'Date parameter is missing'}, status=400)

    try:
        selected_date = datetime.datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Invalid date format. Use<\ctrl97>-MM-DD'}, status=400)

    settings = SiteSettings.get_settings()
    today = timezone.now().date()
    min_booking_date = today + timedelta(days=settings.booking_advance_notice)
    max_booking_date = today + timedelta(days=settings.booking_open_days)

    # Re-validate the date on the backend for this AJAX call for security
    if not (min_booking_date <= selected_date <= max_booking_date):
         return JsonResponse({'error': 'Date is outside the allowed booking range'}, status=400)

    # Check if the date is blocked by admin
    is_blocked_by_admin = BlockedDate.objects.filter(
        start_date__lte=selected_date,
        end_date__gte=selected_date
    ).exists()
    if is_blocked_by_admin:
        return JsonResponse({'error': 'This date is blocked'}, status=400)

    # Check if the day is full based on max_visible_slots_per_day
    # This check IS still needed here to prevent selection on a full day even via AJAX
    total_bookings_on_date = ServiceBooking.objects.filter(
        appointment_date=selected_date
    ).count()

    if settings.max_visible_slots_per_day is not None and settings.max_visible_slots_per_day > 0 and \
       total_bookings_on_date >= settings.max_visible_slots_per_day:
         # Although the date should be disabled in the UI, this backend check
         # prevents booking if someone bypasses frontend validation.
         return JsonResponse({'error': 'This date is full'}, status=400)


    # If date is valid and not full, generate all potential time slots for the day
    # We no longer filter by per-slot capacity here
    all_potential_slots = generate_potential_time_slots(selected_date)

    # Format slots for JSON response as a list of {value: 'HH:MM', text: 'HH:MM AM/PM'}
    formatted_slots = [{'value': slot[0], 'text': slot[1]} for slot in all_potential_slots]

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

        # --- Populate time choices before validating on POST ---
        # Get the selected date from the POST data
        selected_date_str_from_post = request.POST.get('appointment_date')
        # Initialize lists for form choices and template JSON
        time_slots_for_form_choices = [] # List of (value, text) tuples for form choices
        available_time_slots_json_for_template = [] # List of {value: 'HH:MM', text: 'HH:MM AM/PM'} for template JSON

        if selected_date_str_from_post:
            try:
                # Parse the date string
                selected_date_from_post = datetime.datetime.strptime(selected_date_str_from_post, '%Y-%m-%d').date()

                # --- Backend check for daily capacity on POST ---
                total_bookings_on_date = ServiceBooking.objects.filter(
                    appointment_date=selected_date_from_post
                ).count()

                if settings.max_visible_slots_per_day is not None and settings.max_visible_slots_per_day > 0 and \
                   total_bookings_on_date >= settings.max_visible_slots_per_day:
                     # If the day is full, add a form error and don't populate slots
                     form.add_error('appointment_date', 'This date is already fully booked.')
                     # time_slots_for_form_choices and available_time_slots_json_for_template remain []

                else:
                    # If the day is not full, generate all potential time slots for the date
                    # We no longer filter by per-slot capacity here
                    time_slots_for_form_choices = generate_potential_time_slots(selected_date_from_post)
                    # Also format for the frontend JS if date was valid and not full
                    available_time_slots_json_for_template = [{'value': slot[0], 'text': slot[1]} for slot in time_slots_for_form_choices]

                # Populate the choices for the drop_off_time field in the form instance regardless of full or not
                # If the date was full, this list will be empty, preventing selection.
                form.fields['drop_off_time'].choices = time_slots_for_form_choices


            except ValueError:
                # If the date format is invalid, the form will handle it,
                # but we won't be able to populate time slots dynamically here.
                # time_slots_for_form_choices and available_time_slots_json_for_template remain []
                pass # Let form validation handle the date error

        # --- End Populate Choices Fix ---

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
                     'available_time_slots_json': json.dumps(available_time_slots_json_for_template)
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
                     'available_time_slots_json': json.dumps(available_time_slots_json_for_template)
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
            # by the logic added before form.is_valid() if the date was valid and not full.
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

        # --- Retrieve service_type_id from session and set initial value ---
        # Check if service_type_id is in the session data
        if 'service_type_id' in booking_data:
            try:
                # Get the ServiceType instance
                service_type_instance = ServiceType.objects.get(id=booking_data['service_type_id'])
                # Set the initial value for the service_type field
                form.initial['service_type'] = service_type_instance
            except ServiceType.DoesNotExist:
                # Handle the case where the service type ID in the session is invalid
                messages.warning(request, "The pre-selected service type was not found.")
                # Optionally remove the invalid service_type_id from the session
                if 'service_type_id' in request.session.get(SERVICE_BOOKING_SESSION_KEY, {}):
                     del request.session[SERVICE_BOOKING_SESSION_KEY]['service_type_id']
                     request.session.modified = True

        # --- End Retrieve service_type_id ---


        time_slots_for_form_choices = [] # List of (value, text) tuples for form choices
        available_time_slots_json_for_template = [] # Initialize for template context

        # On GET, if a date was previously selected (e.g., returning to this step),
        # populate the time slots for that date.
        appointment_date_str = initial_data.get('appointment_date_str')
        if appointment_date_str:
             try:
                appointment_date = datetime.datetime.fromisoformat(appointment_date_str).date()

                # --- Check if the date is full on GET (if returning to the page) ---
                settings = SiteSettings.get_settings() # Ensure settings are available here
                total_bookings_on_date = ServiceBooking.objects.filter(
                    appointment_date=appointment_date
                ).count()

                if settings.max_visible_slots_per_day is not None and settings.max_visible_slots_per_day > 0 and \
                   total_bookings_on_date >= settings.max_visible_slots_per_day:
                    # If the previously selected date is now full, clear it from initial data
                    form.initial.pop('appointment_date', None)
                    form.initial.pop('drop_off_time', None)
                    messages.warning(request, f"Your previously selected date {appointment_date.strftime('%Y-%m-%d')} is now fully booked. Please select a new date.")
                    # time_slots_for_form_choices and available_time_slots_json_for_template remain []
                else:
                    # If the date is not full, generate all potential time slots
                    # We no longer filter by per-slot capacity here
                    time_slots_for_form_choices = generate_potential_time_slots(appointment_date)
                    # Populate time choices for the form
                    form.fields['drop_off_time'].choices = time_slots_for_form_choices
                    # Set the initial value for drop_off_time if it exists in session
                    initial_drop_off_time = initial_data.get('drop_off_time_str')
                    # Only set initial value if it's one of the available choices
                    if initial_drop_off_time and any(slot[0] == initial_drop_off_time for slot in time_slots_for_form_choices):
                         form.initial['drop_off_time'] = initial_drop_off_time
                    else:
                         # If the stored time is no longer available, clear it from initial data
                         form.initial.pop('drop_off_time', None)

                    # Also format for the frontend JS if date was in session and not full
                    available_time_slots_json_for_template = [{'value': slot[0], 'text': slot[1]} for slot in time_slots_for_form_choices]


             except (ValueError, TypeError):
                 # Handle cases where session date data is invalid
                 form.initial.pop('appointment_date', None) # Clear invalid date
                 form.initial.pop('drop_off_time', None) # Clear associated time
                 messages.warning(request, "Your previously selected date was invalid. Please select a new date.")
                 # time_slots_for_form_choices and available_time_slots_json_for_template remain [] due to initial assignment
                 pass


    # Pass necessary data to the template for Flatpickr configuration and initial time slot population
    # This is outside the if appointment_date_str: block
    settings = SiteSettings.get_settings()
    blocked_dates_by_admin = BlockedDate.objects.all()
    blocked_date_ranges_admin = []
    for blocked in blocked_dates_by_admin:
         blocked_date_ranges_admin.append({
             'from': blocked.start_date.strftime('%Y-%m-%d'),
             'to': blocked.end_date.strftime('%Y-%m-%d')
         })

    # Get dates disabled due to daily capacity
    disabled_dates_by_capacity = get_disabled_dates_by_capacity()

    # Combine admin blocked dates and capacity disabled dates for Flatpickr
    all_disabled_dates_for_flatpickr = blocked_date_ranges_admin + disabled_dates_by_capacity


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
        # Pass ALL disabled dates (admin + capacity) to template for Flatpickr
        'blocked_date_ranges_json': json.dumps(all_disabled_dates_for_flatpickr),
        'min_date': min_date.strftime('%Y-%m-%d'), # Pass min date to template
        'max_date': max_date.strftime('%Y-%m-%d'), # Pass max date to template
        # Pass initial available slots to template for frontend JS to populate
        'available_time_slots_json': json.dumps(available_time_slots_json_for_template)
    }
    return render(request, 'service/service_details.html', context)