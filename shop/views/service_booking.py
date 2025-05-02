# core/views/service_booking.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
import datetime
from django.db.models import Q
# from django.core.mail import send_mail # Commented out email imports
# from django.template.loader import render_to_string # Commented out email imports
# from django.utils.html import strip_tags # Commented out email imports
from ..models import ServiceBooking, CustomerMotorcycle, ServiceType, SiteSettings # Import models
from ..forms import ServiceDetailsForm, CustomerMotorcycleForm, ServiceBookingUserForm, ExistingCustomerMotorcycleForm # Import forms
from django.contrib.auth.decorators import login_required # Import login_required

# Define a session key for service booking data
SERVICE_BOOKING_SESSION_KEY = 'service_booking_data'

def service_booking_start(request):
    settings = SiteSettings.get_settings()
    if not settings.enable_service_booking:
        messages.error(request, "Service booking is currently disabled.")
        return redirect('shop:index') # Or a dedicated service disabled page

    # Clear any previous booking data from the session
    if SERVICE_BOOKING_SESSION_KEY in request.session:
        del request.session[SERVICE_BOOKING_SESSION_KEY]
    request.session.modified = True # Ensure session is saved

    # Redirect based on authentication and anonymous booking setting
    if request.user.is_authenticated:
        # Logged-in users always go to the authenticated flow
        return redirect('shop:service_booking_step1_authenticated')
    elif settings.allow_anonymous_bookings:
        # Anonymous users go to the anonymous flow if allowed
        return redirect('shop:service_booking_step1_anonymous')
    else:
        # Anonymous bookings not allowed, prompt login
        messages.info(request, "Please log in or register to book a service.")
        return redirect('shop:login') # Assuming 'login' is the name of your login URL pattern


# Step 1: Booking Information (Service Type, Date & Time) - Authenticated
@login_required
def service_booking_step1_authenticated(request):
    settings = SiteSettings.get_settings()
    if not settings.enable_service_booking:
        messages.error(request, "Service booking is currently disabled.")
        return redirect('shop:index')

    # Retrieve data from session if available
    booking_data = request.session.get(SERVICE_BOOKING_SESSION_KEY, {})

    if request.method == 'POST':
        form = ServiceDetailsForm(request.POST)
        if form.is_valid():
            cleaned_data = form.cleaned_data.copy()
            cleaned_data['service_type_id'] = cleaned_data['service_type'].id
            del cleaned_data['service_type']

            if 'appointment_datetime' in cleaned_data and isinstance(cleaned_data['appointment_datetime'], datetime.datetime):
                cleaned_data['appointment_datetime_str'] = cleaned_data['appointment_datetime'].isoformat()
                del cleaned_data['appointment_datetime']

            # Store ALL cleaned data in session for this step
            booking_data.update(cleaned_data)
            request.session[SERVICE_BOOKING_SESSION_KEY] = booking_data
            request.session.modified = True

            # Proceed to step 2 (Vehicle Details) for authenticated users
            return redirect('shop:service_booking_step2_authenticated')
    else:
        # GET request: Pre-fill form with session data
        initial_data = booking_data.copy() # Use a copy to avoid modifying session directly

        if 'appointment_datetime_str' in initial_data:
             try:
                initial_data['appointment_datetime'] = datetime.datetime.fromisoformat(initial_data['appointment_datetime_str'])
                del initial_data['appointment_datetime_str'] # Remove the string version after converting
             except (ValueError, TypeError):
                 pass # Handle conversion errors gracefully


        form = ServiceDetailsForm(initial=initial_data)

    context = {
        'form': form,
        'step': 1,
        'total_steps': 3,
        'is_authenticated': True,
        'allow_anonymous_bookings': settings.allow_anonymous_bookings, # Still pass this for context
    }
    return render(request, 'service_booking/service_details_authenticated.html', context)

# Step 1: Booking Information (Service Type, Date & Time) - Anonymous
def service_booking_step1_anonymous(request):
    settings = SiteSettings.get_settings()
    if not settings.enable_service_booking:
        messages.error(request, "Service booking is currently disabled.")
        return redirect('shop:index')
    if not settings.allow_anonymous_bookings:
         messages.error(request, "Anonymous bookings are not allowed.")
         return redirect('shop:service_booking_start') # Go back to start, which redirects to login

    # Retrieve data from session if available
    booking_data = request.session.get(SERVICE_BOOKING_SESSION_KEY, {})

    if request.method == 'POST':
        form = ServiceDetailsForm(request.POST)
        if form.is_valid():
            cleaned_data = form.cleaned_data.copy()
            cleaned_data['service_type_id'] = cleaned_data['service_type'].id
            del cleaned_data['service_type']

            if 'appointment_datetime' in cleaned_data and isinstance(cleaned_data['appointment_datetime'], datetime.datetime):
                cleaned_data['appointment_datetime_str'] = cleaned_data['appointment_datetime'].isoformat()
                del cleaned_data['appointment_datetime']

            # Store ALL cleaned data in session for this step
            booking_data.update(cleaned_data)
            request.session[SERVICE_BOOKING_SESSION_KEY] = booking_data
            request.session.modified = True


            # Proceed to step 2 (Vehicle Details) for anonymous users
            return redirect('shop:service_booking_step2_anonymous')
    else:
         # GET request: Pre-fill form with session data
        initial_data = booking_data.copy()

        if 'appointment_datetime_str' in initial_data:
             try:
                initial_data['appointment_datetime'] = datetime.datetime.fromisoformat(initial_data['appointment_datetime_str'])
                del initial_data['appointment_datetime_str']
             except (ValueError, TypeError):
                 pass

        form = ServiceDetailsForm(initial=initial_data)

    context = {
        'form': form,
        'step': 1,
        'total_steps': 3,
        'is_authenticated': False,
        'allow_anonymous_bookings': settings.allow_anonymous_bookings,
    }
    return render(request, 'service_booking/service_details_anonymous.html', context)


# Step 2: Vehicle Details - Authenticated
@login_required
def service_booking_step2_authenticated(request):
    settings = SiteSettings.get_settings()
    if not settings.enable_service_booking:
        messages.error(request, "Service booking is currently disabled.")
        return redirect('shop:index')

    # Retrieve data from step 1
    booking_data = request.session.get(SERVICE_BOOKING_SESSION_KEY)
    if not booking_data:
        messages.warning(request, "Please start the booking process again.")
        return redirect('shop:service_booking_step1_authenticated')

    user = request.user
    user_motorcycles = CustomerMotorcycle.objects.filter(owner=user)
    has_existing_bikes = user_motorcycles.exists()

    # We will have two separate forms on the page, each submitting to this view.
    # The view logic needs to determine which form was submitted.
    # A simple way is to check for a field that is unique to each form in POST data.
    # ExistingCustomerMotorcycleForm has 'motorcycle'. CustomerMotorcycleForm has 'make', 'model', 'year'.

    existing_bike_form = ExistingCustomerMotorcycleForm(user=user) if has_existing_bikes else None
    new_bike_form = CustomerMotorcycleForm()

    if request.method == 'POST':
        # Determine which form was likely submitted
        if 'motorcycle' in request.POST and has_existing_bikes:
             # User likely submitted the existing bike form
             existing_bike_form = ExistingCustomerMotorcycleForm(request.POST, user=user)
             if existing_bike_form.is_valid():
                selected_motorcycle = existing_bike_form.cleaned_data['motorcycle']
                booking_data['vehicle_id'] = selected_motorcycle.id
                # Remove any anonymous vehicle data just in case
                booking_data.pop('anon_vehicle_make', None)
                booking_data.pop('anon_vehicle_model', None)
                booking_data.pop('anon_vehicle_year', None)
                booking_data.pop('anon_vehicle_rego', None)
                booking_data.pop('anon_vehicle_vin_number', None)
                booking_data.pop('anon_vehicle_odometer', None)
                booking_data.pop('anon_vehicle_transmission', None)

                request.session[SERVICE_BOOKING_SESSION_KEY] = booking_data
                request.session.modified = True
                return redirect('shop:service_booking_step3_authenticated')
             else:
                 messages.error(request, "Please select a valid existing motorcycle.")
                 # Keep the new_bike_form instantiated for rendering
                 new_bike_form = CustomerMotorcycleForm()


        elif 'make' in request.POST or 'model' in request.POST or 'year' in request.POST:
            # User likely submitted the new bike form (check for fields present in that form)
            new_bike_form = CustomerMotorcycleForm(request.POST)
            # Keep the existing_bike_form instantiated for rendering if applicable
            existing_bike_form = ExistingCustomerMotorcycleForm(user=user) if has_existing_bikes else None

            if new_bike_form.is_valid():
                new_motorcycle = new_bike_form.save(commit=False)
                new_motorcycle.owner = user # Assign the logged-in user
                new_motorcycle.save()
                booking_data['vehicle_id'] = new_motorcycle.id
                 # Remove any anonymous vehicle data just in case
                booking_data.pop('anon_vehicle_make', None)
                booking_data.pop('anon_vehicle_model', None)
                booking_data.pop('anon_vehicle_year', None)
                booking_data.pop('anon_vehicle_rego', None)
                booking_data.pop('anon_vehicle_vin_number', None)
                booking_data.pop('anon_vehicle_odometer', None)
                booking_data.pop('anon_vehicle_transmission', None)

                request.session[SERVICE_BOOKING_SESSION_KEY] = booking_data
                request.session.modified = True
                return redirect('shop:service_booking_step3_authenticated')
            else:
                messages.error(request, "Please correct the errors in the new motorcycle details.")

        else:
            # Neither form was clearly submitted or POST data is missing
            messages.error(request, "Invalid form submission.")


    # GET request or POST with errors
    # Check if vehicle_id is in session for initial data (e.g., returning from step 3)
    initial_vehicle_id = booking_data.get('vehicle_id')
    if initial_vehicle_id and has_existing_bikes and existing_bike_form:
         try:
            # Use explicit filter with the user instance
            selected_motorcycle = CustomerMotorcycle.objects.get(id=initial_vehicle_id, owner=user)
            existing_bike_form.initial['motorcycle'] = selected_motorcycle
         except CustomerMotorcycle.DoesNotExist:
            pass # Motorcycle not found, leave initial data empty


    context = {
        'existing_bike_form': existing_bike_form,
        'new_bike_form': new_bike_form,
        'step': 2,
        'total_steps': 3,
        'is_authenticated': True,
        'has_existing_bikes': has_existing_bikes,
    }
    return render(request, 'service_booking/service_bike_details_authenticated.html', context)

# Step 2: Vehicle Details - Anonymous
def service_booking_step2_anonymous(request):
    settings = SiteSettings.get_settings()
    if not settings.enable_service_booking:
        messages.error(request, "Service booking is currently disabled.")
        return redirect('shop:index')
    if not settings.allow_anonymous_bookings:
         messages.error(request, "Anonymous bookings are not allowed.")
         return redirect('shop:service_booking_start')

    # Retrieve data from step 1
    booking_data = request.session.get(SERVICE_BOOKING_SESSION_KEY)
    if not booking_data:
        messages.warning(request, "Please start the booking process again.")
        return redirect('shop:service_booking_step1_anonymous')

    if request.method == 'POST':
        form = CustomerMotorcycleForm(request.POST)
        if form.is_valid():
            # Store anonymous bike details in session
            booking_data['anon_vehicle_make'] = form.cleaned_data['make']
            booking_data['anon_vehicle_model'] = form.cleaned_data['model']
            booking_data['anon_vehicle_year'] = form.cleaned_data['year']
            booking_data['anon_vehicle_rego'] = form.cleaned_data.get('rego')
            booking_data['anon_vehicle_vin_number'] = form.cleaned_data.get('vin_number')
            booking_data['anon_vehicle_odometer'] = form.cleaned_data.get('odometer')
            booking_data['anon_vehicle_transmission'] = form.cleaned_data.get('transmission')

             # Remove any linked vehicle data just in case (shouldn't happen for anon)
            booking_data.pop('vehicle_id', None)


            request.session[SERVICE_BOOKING_SESSION_KEY] = booking_data
            request.session.modified = True
            # Proceed to step 3 for anonymous users
            return redirect('shop:service_booking_step3_anonymous')
        else:
            messages.error(request, "Please correct the errors in the vehicle details.")
            # Re-render with errors
            context = {
                'form': form, # Pass the form with errors
                'step': 2,
                'total_steps': 3,
                'is_authenticated': False,
                'allow_anonymous_bookings': settings.allow_anonymous_bookings,
            }
            return render(request, 'service_booking/service_bike_details_anonymous.html', context)


    else: # GET request
        # Pre-fill form with session data if available
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

    return render(request, 'service_booking/service_bike_details_anonymous.html', context)


# Step 3: Personal Information - Authenticated
@login_required
def service_booking_step3_authenticated(request):
    settings = SiteSettings.get_settings()
    # Check if service booking is enabled
    if not settings.enable_service_booking:
        messages.error(request, "Service booking is currently disabled.")
        return redirect('shop:index')

    # Retrieve data from previous steps from the session
    booking_data = request.session.get(SERVICE_BOOKING_SESSION_KEY)
    # If session data is missing, redirect to the start of the authenticated flow
    if not booking_data:
        messages.warning(request, "Please start the booking process again.")
        return redirect('shop:service_booking_step1_authenticated')

    user = request.user # Get the logged-in user

    # Initialize the form with session data for GET or with POST data for POST
    # Use a copy of booking_data to avoid modifying the session directly during form processing
    initial_data = booking_data.copy()

    if request.method == 'POST':
        # If the request is POST, instantiate the form with the submitted data
        form = ServiceBookingUserForm(request.POST)
        # For authenticated users, the 'is_returning_customer' field is not needed.
        # Remove it from the form instance before validation and saving.
        if 'is_returning_customer' in form.fields:
             form.fields.pop('is_returning_customer')

        # Validate the form
        if form.is_valid():
            # If the form is valid, update the session data with the cleaned data from the form.
            # This allows the user to edit their contact details for this specific booking.
            booking_data.update(form.cleaned_data)
            request.session[SERVICE_BOOKING_SESSION_KEY] = booking_data
            request.session.modified = True # Ensure the session is marked as modified

            # Process and create the ServiceBooking instance
            service_booking = ServiceBooking()

            # Link the booking to the logged-in customer (User model instance)
            service_booking.customer = user
            # Populate customer details on the booking, using cleaned_data from the form if available,
            # otherwise fall back to the user's profile data.
            service_booking.customer_name = f"{form.cleaned_data.get('first_name', user.first_name)} {form.cleaned_data.get('last_name', user.last_name)}"
            service_booking.customer_email = form.cleaned_data.get('email', user.email)
            # Safely get phone_number using getattr in case the User model doesn't have this field (though yours does)
            service_booking.customer_phone = form.cleaned_data.get('phone_number', getattr(user, 'phone_number', ''))
            # Add address fields if present in ServiceBookingUserForm and session data (assuming you might add these)
            # service_booking.customer_address = booking_data.get('address_field_name') # Example if you add address fields

            # Link the booking to the selected or newly added CustomerMotorcycle using the ID from the session
            vehicle_id = booking_data.get('vehicle_id')
            if vehicle_id:
                try:
                    # Get the CustomerMotorcycle instance; ensure it belongs to the logged-in user for security
                    service_booking.vehicle = CustomerMotorcycle.objects.get(id=vehicle_id, owner=user)
                except CustomerMotorcycle.DoesNotExist:
                    # If the selected motorcycle is not found or doesn't belong to the user, show an error and go back to step 2
                    messages.error(request, "Selected motorcycle not found or does not belong to your account.")
                    return redirect('shop:service_booking_step2_authenticated')
            else:
                 # If vehicle_id is missing from the session (should be set in step 2), redirect back to step 2
                 messages.error(request, "No vehicle selected for service.")
                 return redirect('shop:service_booking_step2_authenticated')

            # Add service details from session
            try:
                service_type_id = booking_data.get('service_type_id')
                if service_type_id:
                    # Get the ServiceType instance using the ID from the session
                    service_booking.service_type = ServiceType.objects.get(id=service_type_id)
                else:
                    # If service_type_id is missing, redirect back to step 1
                    messages.error(request, "Invalid service type selected.")
                    return redirect('shop:service_booking_step1_authenticated')
            except ServiceType.DoesNotExist:
                # If the ServiceType ID from the session is invalid, redirect back to step 1
                messages.error(request, "Invalid service type selected.")
                return redirect('shop:service_booking_step1_authenticated')

            # Convert the stored datetime string back to a datetime object
            if 'appointment_datetime_str' in booking_data:
                try:
                    service_booking.appointment_datetime = datetime.datetime.fromisoformat(
                        booking_data['appointment_datetime_str'])
                except (ValueError, TypeError):
                    # If the stored datetime string is invalid, show an error and go back to step 1
                    messages.error(request, "Invalid appointment date/time. Please select again.")
                    return redirect('shop:service_booking_step1_authenticated')
            else:
                 # If appointment_datetime_str is missing, redirect back to step 1
                 messages.error(request, "Appointment date/time is missing.")
                 return redirect('shop:service_booking_step1_authenticated')


            # Populate other fields from session data
            service_booking.preferred_contact = booking_data.get('preferred_contact')
            service_booking.customer_notes = booking_data.get('booking_comments')

            # Set the initial status of the booking (should default to 'pending' in model, but being explicit)
            service_booking.status = 'pending'

            try:
                # Save the ServiceBooking instance to the database
                service_booking.save()

                # Clear the service booking data from the session after successful save
                if SERVICE_BOOKING_SESSION_KEY in request.session:
                    del request.session[SERVICE_BOOKING_SESSION_KEY]
                request.session.modified = True # Ensure session is saved after clearing

                # Add a success message
                messages.success(request, "Your service booking request has been submitted successfully.")
                # Redirect to the confirmation page
                return redirect('shop:service_booking_not_yet_confirmed')

            except Exception as e:
                # If there's an error during the save process (database issue, etc.)
                # Log the error and show a user-friendly message
                print(f"Error saving booking: {e}") # Log the error to the console/logs
                messages.error(request, f"There was an error saving your booking. Please try again. Error: {e}")
                # Re-render the form with the data they submitted, including any save errors
                # The invalid form instance will contain non-field errors if any occurred during save
                context = {
                    'step': 3,
                    'total_steps': 3,
                    'form': form, # Pass the form with their POST data (and potentially save errors)
                    'is_authenticated': True,
                }
                return render(request, 'service_booking/service_user_details_authenticated.html', context)

        else: # If the form is NOT valid on POST
             # Add a general error message indicating form errors
             messages.error(request, "Please correct the errors below.")
             # The invalid form instance, containing field-specific errors, is automatically
             # passed to the template for rendering.

    else: # GET request (User arriving at this step for the first time or returning from subsequent step)
        # Instantiate the form. Django will use the 'initial' data provided.
        initial_data = booking_data.copy()

        # Pre-fill core contact fields from the user's profile, overriding any session data
        initial_data['first_name'] = user.first_name
        initial_data['last_name'] = user.last_name
        initial_data['email'] = user.email
        initial_data['phone_number'] = getattr(user, 'phone_number', '')
        # Preferred contact and comments are pre-filled from the session data (initial_data) if available

        form = ServiceBookingUserForm(initial=initial_data)
        # Remove the 'is_returning_customer' field for display on the GET request
        if 'is_returning_customer' in form.fields:
            form.fields.pop('is_returning_customer')

    # Prepare the context to render the template
    context = {
        'form': form, # The form instance (either empty, pre-filled, or with errors)
        'step': 3,
        'total_steps': 3,
        'is_authenticated': True, # Indicate that the user is authenticated
        # 'allow_anonymous_bookings': settings.allow_anonymous_bookings, # Not strictly needed in authenticated flow context
    }
    return render(request, 'service_booking/service_user_details_authenticated.html', context)

# Step 3: Personal Information - Anonymous
def service_booking_step3_anonymous(request):
    settings = SiteSettings.get_settings()
    if not settings.enable_service_booking:
        messages.error(request, "Service booking is currently disabled.")
        return redirect('shop:index')
    if not settings.allow_anonymous_bookings:
         messages.error(request, "Anonymous bookings are not allowed.")
         return redirect('shop:service_booking_start')

    # Retrieve data from previous steps
    booking_data = request.session.get(SERVICE_BOOKING_SESSION_KEY)
    if not booking_data:
        messages.warning(request, "Please start the booking process again.")
        return redirect('shop:service_booking_step1_anonymous') # Redirect to step 1 anonymous

    if request.method == 'POST':
        form = ServiceBookingUserForm(request.POST)
        # Ensure the 'is_returning_customer' field is present for anonymous users validation
        # This might already be the case if it's defined in ServiceBookingUserForm base_fields
        # If you removed it in __init__, you might need to add it back here.
        # Based on your forms.py, it's a base field, so it should be present.


        if form.is_valid():
            # Store user details in session
            booking_data.update(form.cleaned_data)
            request.session[SERVICE_BOOKING_SESSION_KEY] = booking_data
            request.session.modified = True

            # Process and create the ServiceBooking
            service_booking = ServiceBooking()

            # Store anonymous customer details
            service_booking.customer_name = f"{form.cleaned_data['first_name']} {form.cleaned_data['last_name']}"
            service_booking.customer_email = form.cleaned_data['email']
            service_booking.customer_phone = form.cleaned_data.get('phone_number')
             # Add address fields if present in ServiceBookingUserForm and session data
            # service_booking.customer_address = ...


            # Store anonymous vehicle details from session
            service_booking.anon_vehicle_make = booking_data.get('anon_vehicle_make')
            service_booking.anon_vehicle_model = booking_data.get('anon_vehicle_model')
            service_booking.anon_vehicle_year = booking_data.get('anon_vehicle_year')
            service_booking.anon_vehicle_rego = booking_data.get('anon_vehicle_rego')
            service_booking.anon_vehicle_vin_number = booking_data.get('anon_vehicle_vin_number') # Added VIN for anonymous
            service_booking.anon_vehicle_odometer = booking_data.get('anon_vehicle_odometer')
            service_booking.anon_vehicle_transmission = booking_data.get('anon_vehicle_transmission')


            # Add service details from session
            try:
                service_type_id = booking_data.get('service_type_id')
                if service_type_id:
                    service_booking.service_type = ServiceType.objects.get(id=service_type_id)
                else:
                    messages.error(request, "Invalid service type selected.")
                    return redirect('shop:service_booking_step1_anonymous')
            except ServiceType.DoesNotExist:
                messages.error(request, "Invalid service type selected.")
                return redirect('shop:service_booking_step1_anonymous')

            # Convert the stored datetime string back to a datetime object
            if 'appointment_datetime_str' in booking_data:
                try:
                    service_booking.appointment_datetime = datetime.datetime.fromisoformat(
                        booking_data['appointment_datetime_str'])
                except (ValueError, TypeError):
                    messages.error(request, "Invalid appointment date/time. Please select again.")
                    return redirect('shop:service_booking_step1_anonymous')

            service_booking.preferred_contact = booking_data.get('preferred_contact')
            service_booking.customer_notes = booking_data.get('booking_comments')

            service_booking.status = 'pending'

            try:
                service_booking.save()

                if SERVICE_BOOKING_SESSION_KEY in request.session:
                    del request.session[SERVICE_BOOKING_SESSION_KEY]
                request.session.modified = True

                messages.success(request, "Your service booking request has been submitted successfully.")
                return redirect('shop:service_booking_not_yet_confirmed')

            except Exception as e:
                print(f"Error saving booking: {e}")
                messages.error(request, f"There was an error saving your booking. Please try again. Error: {e}")
                context = {
                    'step': 3,
                    'total_steps': 3,
                    'form': form,
                    'is_authenticated': False,
                    'allow_anonymous_bookings': settings.allow_anonymous_bookings,
                }
                return render(request, 'service_booking/service_user_details_anonymous.html', context)

    else: # GET request
        initial_data = booking_data.copy()
        form = ServiceBookingUserForm(initial=initial_data)
         # Ensure the 'is_returning_customer' field is present for anonymous users GET request
        # This might already be the case if it's defined in ServiceBookingUserForm base_fields
        # If you removed it in __init__, you might need to add it back here.
        # Based on your forms.py, it's a base field, so it should be present.


    context = {
        'form': form,
        'step': 3,
        'total_steps': 3,
        'is_authenticated': False,
        'allow_anonymous_bookings': settings.allow_anonymous_bookings,
    }
    return render(request, 'service_booking/service_user_details_anonymous.html', context)


# Keep the confirmation view as is
def service_booking_not_yet_confirmed_view(request):
    return render(request, 'service_booking/service_not_yet_confirmed.html')