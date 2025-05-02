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

    return redirect('shop:service_booking_step1') # Assuming 'service_booking_step1' is the name of your URL pattern for the merged view

# Step 1: Booking Information (Service Type, Date & Time) - Merged View
def service_booking_step1(request):
    settings = SiteSettings.get_settings()
    # This check is also in service_booking_start, but good to have here too
    # in case someone accesses step1 directly without going through start.
    if not settings.enable_service_booking:
        messages.error(request, "Service booking is currently disabled.")
        return redirect('shop:index')

    # Check if anonymous bookings are allowed if the user is not authenticated
    # If not allowed and user is not authenticated, redirect to login.
    if not request.user.is_authenticated and not settings.allow_anonymous_bookings:
         messages.info(request, "Please log in or register to book a service.")
         # Use reverse to get the URL for your login page
         return redirect(reverse('shop:login')) # Assuming 'login' is the name of your login URL pattern


    # Retrieve data from session if available
    booking_data = request.session.get(SERVICE_BOOKING_SESSION_KEY, {})

    if request.method == 'POST':
        form = ServiceDetailsForm(request.POST)
        if form.is_valid():
            cleaned_data = form.cleaned_data.copy()
            # Safely get service_type ID after validation
            service_type_instance = cleaned_data.get('service_type')
            if service_type_instance:
                cleaned_data['service_type_id'] = service_type_instance.id
                del cleaned_data['service_type']
            else:
                 # This shouldn't happen if form is valid and service_type is required,
                 # but as a safeguard:
                 messages.error(request, "Invalid service type selected.")
                 # Re-render the form with errors
                 context = {
                     'form': form,
                     'step': 1,
                     'total_steps': 3,
                     'is_authenticated': request.user.is_authenticated,
                     'allow_anonymous_bookings': settings.allow_anonymous_bookings,
                 }
                 return render(request, 'service_booking/service_details.html', context)


            if 'appointment_datetime' in cleaned_data and isinstance(cleaned_data['appointment_datetime'], datetime.datetime):
                cleaned_data['appointment_datetime_str'] = cleaned_data['appointment_datetime'].isoformat()
                del cleaned_data['appointment_datetime']
            else:
                 # This shouldn't happen if form is valid and appointment_datetime is required,
                 # but as a safeguard:
                 messages.error(request, "Invalid appointment date/time.")
                 # Re-render the form with errors
                 context = {
                     'form': form,
                     'step': 1,
                     'total_steps': 3,
                     'is_authenticated': request.user.is_authenticated,
                     'allow_anonymous_bookings': settings.allow_anonymous_bookings,
                 }
                 return render(request, 'service_booking/service_details.html', context)


            # Store ALL cleaned data in session for this step
            booking_data.update(cleaned_data)
            request.session[SERVICE_BOOKING_SESSION_KEY] = booking_data
            request.session.modified = True

            # Redirect based on authentication status to the appropriate step 2
            if request.user.is_authenticated:
                return redirect('shop:service_booking_step2_authenticated')
            else:
                return redirect('shop:service_booking_step2_anonymous')
        else:
            # Form is not valid on POST
            messages.error(request, "Please correct the errors below.")
            # Re-render the template with the form containing errors
            context = {
                'form': form, # Pass the form with errors
                'step': 1,
                'total_steps': 3,
                'is_authenticated': request.user.is_authenticated,
                'allow_anonymous_bookings': settings.allow_anonymous_bookings,
            }
            return render(request, 'service_booking/service_details.html', context)

    else: # GET request
        # Pre-fill form with session data if available
        initial_data = booking_data.copy() # Use a copy to avoid modifying session directly

        # Convert the stored datetime string back to a datetime object for form initialization
        if 'appointment_datetime_str' in initial_data:
             try:
                initial_data['appointment_datetime'] = datetime.datetime.fromisoformat(initial_data['appointment_datetime_str'])
                # No need to delete 'appointment_datetime_str' from initial_data here, as it's just for form display
             except (ValueError, TypeError):
                 # If conversion fails, just don't pre-fill the datetime field
                 pass

        # Safely get the ServiceType instance for form initialization
        service_type_id = initial_data.get('service_type_id')
        if service_type_id:
            try:
                initial_data['service_type'] = ServiceType.objects.get(id=service_type_id)
                # No need to delete 'service_type_id' from initial_data here
            except ServiceType.DoesNotExist:
                # If the ServiceType ID from the session is invalid, don't pre-fill the service_type field
                pass


        form = ServiceDetailsForm(initial=initial_data)

    # Prepare the context for rendering the template
    context = {
        'form': form, # The form instance (either empty, pre-filled, or with errors)
        'step': 1,
        'total_steps': 3,
        'is_authenticated': request.user.is_authenticated, # Pass authentication status to template
        'allow_anonymous_bookings': settings.allow_anonymous_bookings, # Still useful in context
    }
    # Use the single merged template
    return render(request, 'service_booking/service_details.html', context)

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
        return redirect('shop:service_booking_step1') # Redirect to merged step 1

    user = request.user
    user_motorcycles = CustomerMotorcycle.objects.filter(owner=user)
    has_existing_bikes = user_motorcycles.exists()

    # Initialize forms - we might need one or both depending on the request
    existing_bike_form = ExistingCustomerMotorcycleForm(user=user) if has_existing_bikes else None
    # The motorcycle_form will be the CustomerMotorcycleForm, instantiated based on action
    motorcycle_form = None
    selected_motorcycle = None # To hold the instance if editing existing

    # Determine which section to display initially or after POST
    display_existing_selection = True # Default
    display_motorcycle_details = False

    # Check session for a selected vehicle, which means we should show the details form
    selected_vehicle_id_in_session = booking_data.get('vehicle_id')
    if selected_vehicle_id_in_session:
         try:
            # Verify the motorcycle in the session belongs to the user
            selected_motorcycle = CustomerMotorcycle.objects.get(id=selected_vehicle_id_in_session, owner=user)
            # If found, we should display the details form pre-filled
            motorcycle_form = CustomerMotorcycleForm(instance=selected_motorcycle)
            display_existing_selection = False
            display_motorcycle_details = True
         except CustomerMotorcycle.DoesNotExist:
            # If the motorcycle in the session is invalid, clear it
            booking_data.pop('vehicle_id', None)
            request.session[SERVICE_BOOKING_SESSION_KEY] = booking_data
            request.session.modified = True
            messages.warning(request, "Selected motorcycle not found. Please choose again.")
            # Keep default display

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'select_existing' and has_existing_bikes:
            existing_bike_form = ExistingCustomerMotorcycleForm(request.POST, user=user)
            if existing_bike_form.is_valid():
                selected_motorcycle = existing_bike_form.cleaned_data['motorcycle']
                # Store the selected motorcycle's ID in the session
                booking_data['vehicle_id'] = selected_motorcycle.id
                request.session[SERVICE_BOOKING_SESSION_KEY] = booking_data
                request.session.modified = True

                # Instantiate the details form with the selected motorcycle's data
                motorcycle_form = CustomerMotorcycleForm(instance=selected_motorcycle)
                display_existing_selection = False
                display_motorcycle_details = True
                messages.info(request, f"Details for {selected_motorcycle} loaded. You can edit them if needed.")

            else:
                messages.error(request, "Please select a valid existing motorcycle.")
                # Stay on the existing selection view, form will show errors
                display_existing_selection = True
                display_motorcycle_details = False


        elif action == 'add_new':
            motorcycle_form = CustomerMotorcycleForm(request.POST)
            display_existing_selection = False
            display_motorcycle_details = True # Keep details form visible on error

            if motorcycle_form.is_valid():
                new_motorcycle = motorcycle_form.save(commit=False)
                new_motorcycle.owner = user # Assign the logged-in user
                new_motorcycle.save()
                # Store the new motorcycle's ID in the session
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
                messages.success(request, "New motorcycle added.")
                return redirect('shop:service_booking_step3_authenticated')
            else:
                messages.error(request, "Please correct the errors in the new motorcycle details.")


        elif action == 'edit_existing':
            # Ensure a vehicle_id is in the session for this action
            vehicle_id_to_edit = booking_data.get('vehicle_id')
            if not vehicle_id_to_edit:
                 messages.error(request, "No motorcycle selected for editing.")
                 return redirect('shop:service_booking_step2_authenticated') # Go back to selection

            try:
                 selected_motorcycle = CustomerMotorcycle.objects.get(id=vehicle_id_to_edit, owner=user)
                 motorcycle_form = CustomerMotorcycleForm(request.POST, instance=selected_motorcycle)
                 display_existing_selection = False
                 display_motorcycle_details = True # Keep details form visible on error

                 if motorcycle_form.is_valid():
                    motorcycle_form.save() # Save changes to the existing instance
                    messages.success(request, "Motorcycle details updated.")
                    # The vehicle_id is already in the session, proceed to step 3
                    return redirect('shop:service_booking_step3_authenticated')
                 else:
                    messages.error(request, "Please correct the errors in the motorcycle details.")

            except CustomerMotorcycle.DoesNotExist:
                 messages.error(request, "Motorcycle not found for editing.")
                 # Clear invalid vehicle_id from session
                 booking_data.pop('vehicle_id', None)
                 request.session[SERVICE_BOOKING_SESSION_KEY] = booking_data
                 request.session.modified = True
                 return redirect('shop:service_booking_step2_authenticated')


        else: # POST without a valid action
            messages.error(request, "Invalid request.")
            # Stay on the current step, forms will be re-rendered based on initial state or session


    # GET request or POST with errors - prepare context for rendering
    context = {
        'existing_bike_form': existing_bike_form,
        'motorcycle_form': motorcycle_form, # Pass the details form if instantiated
        'step': 2,
        'total_steps': 3,
        'is_authenticated': True,
        'has_existing_bikes': has_existing_bikes,
        'display_existing_selection': display_existing_selection, # Control visibility in template
        'display_motorcycle_details': display_motorcycle_details, # Control visibility in template
        'editing_motorcycle': selected_motorcycle, # Pass the instance if editing
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
        return redirect('shop:service_booking_step1_anonymous') # Redirect to step 1 anonymous

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
            # Update user instance with form data
            user.first_name = form.cleaned_data.get('first_name', user.first_name)
            user.last_name = form.cleaned_data.get('last_name', user.last_name)
            user.email = form.cleaned_data.get('email', user.email)
            user.phone_number = form.cleaned_data.get('phone_number', getattr(user, 'phone_number', ''))

            # Save the user instance
            try:
                user.save()
                messages.success(request, "Your profile details have been updated.")
            except Exception as e:
                 messages.error(request, f"There was an error updating your profile: {e}")
                 # Decide how to handle this error - perhaps re-render the page with an error message

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