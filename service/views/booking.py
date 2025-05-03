# service/views/booking.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
import datetime
from django.db.models import Q
# from django.core.mail import send_mail # Commented out email imports
# from django.template.loader import render_to_string # Commented out email imports
# from django.utils.html import strip_tags # Commented out email imports

# Updated Model Imports (assuming these are correct after your move)
from service.models import ServiceBooking, CustomerMotorcycle, ServiceType
from core.models import SiteSettings # SiteSettings remains in the core app

# Updated Form Imports (Assuming forms are moved from core/forms.py to service/forms.py)
# You will need to manually move the relevant forms from core/forms.py to service/forms.py
from service.forms import (
    ServiceDetailsForm,
    CustomerMotorcycleForm,
    ServiceBookingUserForm,
    ExistingCustomerMotorcycleForm,
)

from django.contrib.auth.decorators import login_required # Import login_required

# Define a session key for service booking data
SERVICE_BOOKING_SESSION_KEY = 'service_booking_data'

# Renamed function
def booking_start(request):
    settings = SiteSettings.get_settings()
    if not settings.enable_service_booking:
        messages.error(request, "Service booking is currently disabled.")
        # Redirect to the core index view (no namespace needed)
        return redirect(reverse('index'))

    # Clear any previous booking data from the session
    if SERVICE_BOOKING_SESSION_KEY in request.session:
        del request.session[SERVICE_BOOKING_SESSION_KEY]
    request.session.modified = True # Ensure session is saved

    # Redirect to the service app's step1 view with service namespace and new URL name
    return redirect(reverse('service:service_step1'))

# Step 1: Booking Information (Service Type, Date & Time) - Merged View
# Renamed function
def booking_step1(request):
    settings = SiteSettings.get_settings()
    # This check is also in booking_start, but good to have here too
    # in case someone accesses step1 directly without going through start.
    if not settings.enable_service_booking:
        messages.error(request, "Service booking is currently disabled.")
        # Redirect to the core index view (no namespace needed)
        return redirect(reverse('index'))

    # Check if anonymous bookings are allowed if the user is not authenticated
    # If not allowed and user is not authenticated, redirect to login.
    if not request.user.is_authenticated and not settings.allow_anonymous_bookings:
         messages.info(request, "Please log in or register to book a service.")
         # Redirect to the users app's login view (no namespace needed as per main urls)
         return redirect(reverse('login'))


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
                 # Template path updated to 'service/...'
                 return render(request, 'service/service_details.html', context)


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
                 # Template path updated to 'service/...'
                 return render(request, 'service/service_details.html', context)


            # Store ALL cleaned data in session for this step
            booking_data.update(cleaned_data)
            request.session[SERVICE_BOOKING_SESSION_KEY] = booking_data
            request.session.modified = True

            # Redirect based on authentication status to the appropriate step 2
            if request.user.is_authenticated:
                 # Redirect with service namespace and new URL name
                return redirect(reverse('service:service_step2_authenticated'))
            else:
                 # Redirect with service namespace and new URL name
                return redirect(reverse('service:service_step2_anonymous'))
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
            # Template path updated to 'service/...'
            return render(request, 'service/service_details.html', context)

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
                service_type_instance = ServiceType.objects.get(id=service_type_id) # Use the correct model import
                initial_data['service_type'] = service_type_instance
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
    # Template path updated to 'service/...'
    return render(request, 'service/service_details.html', context)

# Step 2: Vehicle Details - Authenticated
# Renamed function
@login_required
def booking_step2_authenticated(request):
    settings = SiteSettings.get_settings()
    if not settings.enable_service_booking:
        messages.error(request, "Service booking is currently disabled.")
        # Redirect to the core index view (no namespace needed)
        return redirect(reverse('index'))

    # Retrieve data from step 1
    booking_data = request.session.get(SERVICE_BOOKING_SESSION_KEY)
    if not booking_data:
        messages.warning(request, "Please start the booking process again.")
        # Redirect with service namespace and new URL name
        return redirect(reverse('service:service_step1'))

    user = request.user
     # Use the correct CustomerMotorcycle model import
    user_motorcycles = CustomerMotorcycle.objects.filter(owner=user)
    has_existing_bikes = user_motorcycles.exists()

    # Initialize forms - we might need one or both depending on the request
    existing_bike_form = None
    motorcycle_form = None
    selected_motorcycle = None

    # Determine which section to display initially or after POST
    display_existing_selection = True
    display_motorcycle_details = False
    editing_motorcycle = None # To pass the instance to the template if editing

    # --- GET Request Logic ---
    if request.method == 'GET':
        # Check if the user has existing bikes
        if has_existing_bikes:
            # If yes, show the selection form first
             # Use the correct form import
            existing_bike_form = ExistingCustomerMotorcycleForm(user=user)
            # Always instantiate an empty motorcycle_form for the 'Add New' option on GET
             # Use the correct form import
            motorcycle_form = CustomerMotorcycleForm()
            display_existing_selection = True
            display_motorcycle_details = False

            # Clear any previous vehicle selection or edit mode from the session for step 2 on GET
            # This is crucial to ensure a clean state when the user arrives at step 2 via GET
            booking_data.pop('vehicle_id', None)
            booking_data['edit_motorcycle_mode'] = False
            request.session[SERVICE_BOOKING_SESSION_KEY] = booking_data
            request.session.modified = True

        else:
            # If no existing bikes, show the add new form directly
            # Instantiate an empty motorcycle_form as there's no existing bike to edit
             # Use the correct form import
            motorcycle_form = CustomerMotorcycleForm()
            display_existing_selection = False
            display_motorcycle_details = True
            messages.info(request, "Please provide details for your motorcycle.")
            # Ensure edit_motorcycle_mode is False when adding a new bike
            booking_data['edit_motorcycle_mode'] = False
            # Remove any vehicle_id just in case (shouldn't be present if no bikes exist, but as safeguard)
            booking_data.pop('vehicle_id', None)
            request.session[SERVICE_BOOKING_SESSION_KEY] = booking_data
            request.session.modified = True


    # --- POST Request Logic ---
    elif request.method == 'POST':
        action = request.POST.get('action')

        if action == 'select_existing' and has_existing_bikes:
             # Use the correct form import
            existing_bike_form = ExistingCustomerMotorcycleForm(request.POST, user=user)
            if existing_bike_form.is_valid():
                selected_motorcycle = existing_bike_form.cleaned_data['motorcycle']
                # Store the selected motorcycle's ID in the session
                booking_data['vehicle_id'] = selected_motorcycle.id
                # Set edit mode flag
                booking_data['edit_motorcycle_mode'] = True
                request.session[SERVICE_BOOKING_SESSION_KEY] = booking_data
                request.session.modified = True

                # Instantiate the details form with the selected motorcycle's data
                 # Use the correct form import
                motorcycle_form = CustomerMotorcycleForm(instance=selected_motorcycle)
                editing_motorcycle = selected_motorcycle # Pass instance to template
                display_existing_selection = False
                display_motorcycle_details = True
                messages.info(request, f"Details for {selected_motorcycle} loaded. Please confirm or update them if needed.")
            else:
                # If selection form is invalid, stay on selection screen
                messages.error(request, "Please select a valid existing motorcycle.")
                display_existing_selection = True
                display_motorcycle_details = False
                # Re-instantiate the selection form with errors
                 # Use the correct form import
                existing_bike_form = ExistingCustomerMotorcycleForm(request.POST, user=user)
                # Instantiate an empty motorcycle form in case the user switches to add new
                # THIS IS CRUCIAL: provide a blank form if the selection failed
                 # Use the correct form import
                motorcycle_form = CustomerMotorcycleForm()


        elif action == 'add_new':
            # Important: Do NOT pass an instance here to ensure a new motorcycle is created
             # Use the correct form import
            motorcycle_form = CustomerMotorcycleForm(request.POST)
            display_existing_selection = False
            display_motorcycle_details = True

            # Reset the edit_motorcycle_mode flag to ensure we're in add mode
            booking_data['edit_motorcycle_mode'] = False
            # Remove any vehicle_id to prevent accidental editing
            booking_data.pop('vehicle_id', None)
            request.session[SERVICE_BOOKING_SESSION_KEY] = booking_data
            request.session.modified = True

            if motorcycle_form.is_valid():
                # Create a new instance (never update an existing one in 'add_new' mode)
                new_motorcycle = motorcycle_form.save(commit=False)
                new_motorcycle.owner = user
                new_motorcycle.save()

                # Store the new motorcycle's ID in the session
                booking_data['vehicle_id'] = new_motorcycle.id
                # Set edit mode for future requests to avoid creating duplicates
                booking_data['edit_motorcycle_mode'] = True
                 # Remove any anonymous vehicle data (shouldn't be present for auth user, but as safeguard)
                for key in ['anon_vehicle_make', 'anon_vehicle_model', 'anon_vehicle_year',
                           'anon_vehicle_rego', 'anon_vehicle_vin_number',
                           'anon_vehicle_odometer', 'anon_vehicle_transmission']:
                    booking_data.pop(key, None)


                request.session[SERVICE_BOOKING_SESSION_KEY] = booking_data
                request.session.modified = True
                messages.success(request, "New motorcycle added successfully.")
                 # Redirect with service namespace and new URL name
                return redirect(reverse('service:service_step3_authenticated'))
            else:
                messages.error(request, "Please correct the errors in the new motorcycle details.")
                if has_existing_bikes:
                    # Re-instantiate the selection form for the template
                     # Use the correct form import
                    existing_bike_form = ExistingCustomerMotorcycleForm(user=user)
                    # Instantiate an empty motorcycle form in case the user switches to add new
                    # THIS IS CRUCIAL: provide a blank form for the 'Add New' option
                     # Use the correct form import
                    motorcycle_form = CustomerMotorcycleForm()


        elif action == 'edit_existing':
            # Ensure a vehicle_id is in the session for this action
            vehicle_id_to_edit = booking_data.get('vehicle_id')
            if not vehicle_id_to_edit:
                messages.error(request, "No motorcycle selected for editing.")
                # Redirect back to step 2, which will show selection if available
                 # Redirect with service namespace and new URL name
                return redirect(reverse('service:service_step2_authenticated'))

            try:
                 # Use the correct CustomerMotorcycle model import
                selected_motorcycle = CustomerMotorcycle.objects.get(id=vehicle_id_to_edit, owner=user)
                # When editing, instantiate the form with the existing instance and POST data
                 # Use the correct form import
                motorcycle_form = CustomerMotorcycleForm(request.POST, instance=selected_motorcycle)
                editing_motorcycle = selected_motorcycle # Pass instance to template
                display_existing_selection = False
                display_motorcycle_details = True

                # Make sure edit mode is set to true
                booking_data['edit_motorcycle_mode'] = True
                request.session[SERVICE_BOOKING_SESSION_KEY] = booking_data
                request.session.modified = True

                if motorcycle_form.is_valid():
                    motorcycle_form.save()
                    messages.success(request, "Motorcycle details updated successfully.")
                     # Redirect with service namespace and new URL name
                    return redirect(reverse('service:service_step3_authenticated'))
                else:
                    messages.error(request, "Please correct the errors in the motorcycle details.")
                    if has_existing_bikes:
                        # Re-instantiate the selection form, pre-selecting the one being edited
                         # Use the correct form import
                        existing_bike_form = ExistingCustomerMotorcycleForm(
                            user=user,
                            initial={'motorcycle': selected_motorcycle}
                        )
            except CustomerMotorcycle.DoesNotExist: # Use the correct CustomerMotorcycle model import
                messages.error(request, "Motorcycle not found for editing.")
                # Clear session state related to the edited vehicle
                booking_data.pop('vehicle_id', None)
                booking_data['edit_motorcycle_mode'] = False
                request.session[SERVICE_BOOKING_SESSION_KEY] = booking_data
                request.session.modified = True
                # Redirect back to step 2, which will show selection if available
                 # Redirect with service namespace and new URL name
                return redirect(reverse('service:service_step2_authenticated'))
        else:
            messages.error(request, "Invalid request.")
            # Re-instantiate forms based on the user's existing bikes
            if has_existing_bikes:
                 # Use the correct form import
                 existing_bike_form = ExistingCustomerMotorcycleForm(user=user)
                 # Instantiate an empty motorcycle form in case the user switches to add new
                 # THIS IS CRUCIAL: provide a blank form for the 'Add New' option
                 # Use the correct form import
                 motorcycle_form = CustomerMotorcycleForm()
                 display_existing_selection = True
                 display_motorcycle_details = False
            else:
                 # Use the correct form import
                 motorcycle_form = CustomerMotorcycleForm()
                 display_existing_selection = False
                 display_motorcycle_details = True
                 messages.info(request, "Please provide details for your motorcycle.")


    # Prepare context for rendering
    context = {
        'existing_bike_form': existing_bike_form,
        'motorcycle_form': motorcycle_form,
        'step': 2,
        'total_steps': 3,
        'is_authenticated': True,
        'has_existing_bikes': has_existing_bikes,
        'display_existing_selection': display_existing_selection,
        'display_motorcycle_details': display_motorcycle_details,
        'editing_motorcycle': editing_motorcycle, # Pass the selected/edited instance
        'edit_mode': booking_data.get('edit_motorcycle_mode', False) # Pass the mode flag
    }
    # Template path updated to 'service/...'
    return render(request, 'service/service_bike_details_authenticated.html', context)


# Step 2: Vehicle Details - Anonymous
# Renamed function
def booking_step2_anonymous(request):
    settings = SiteSettings.get_settings()
    if not settings.enable_service_booking:
        messages.error(request, "Service booking is currently disabled.")
        # Redirect to the core index view (no namespace needed)
        return redirect(reverse('index'))
    if not settings.allow_anonymous_bookings:
         messages.error(request, "Anonymous bookings are not allowed.")
         # Redirect with service namespace and new URL name
         return redirect(reverse('service:service_start'))

    # Retrieve data from step 1
    booking_data = request.session.get(SERVICE_BOOKING_SESSION_KEY)
    if not booking_data:
        messages.warning(request, "Please start the booking process again.")
        # Redirect with service namespace and new URL name
        return redirect(reverse('service:service_step1'))

    if request.method == 'POST':
        # Use the correct form import
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
             # Ensure edit_motorcycle_mode is False for anonymous users
            booking_data['edit_motorcycle_mode'] = False


            request.session[SERVICE_BOOKING_SESSION_KEY] = booking_data
            request.session.modified = True
            # Proceed to step 3 for anonymous users
             # Redirect with service namespace and new URL name
            return redirect(reverse('service:service_step3_anonymous'))
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
            # Template path updated to 'service/...'
            return render(request, 'service/service_bike_details_anonymous.html', context)


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
        # Use the correct form import
        form = CustomerMotorcycleForm(initial=initial_data)
        context = {
            'form': form,
            'step': 2,
            'total_steps': 3,
            'is_authenticated': False,
            'allow_anonymous_bookings': settings.allow_anonymous_bookings,
        }

    # Template path updated to 'service/...'
    return render(request, 'service/service_bike_details_anonymous.html', context)


# Step 3: Personal Information - Authenticated
# Renamed function
@login_required
def booking_step3_authenticated(request):
    settings = SiteSettings.get_settings()
    # Check if service booking is enabled
    if not settings.enable_service_booking:
        messages.error(request, "Service booking is currently disabled.")
        # Redirect to the core index view (no namespace needed)
        return redirect(reverse('index'))

    # Retrieve data from previous steps from the session
    booking_data = request.session.get(SERVICE_BOOKING_SESSION_KEY)
    # If session data is missing, redirect to the start of the authenticated flow
    if not booking_data:
        messages.warning(request, "Please start the booking process again.")
        # Redirect with service namespace and new URL name
        return redirect(reverse('service:service_step1'))

    user = request.user # Get the logged-in user

    # Initialize the form with session data for GET or with POST data for POST
    # Use a copy of booking_data to avoid modifying the session directly during form processing
    initial_data = booking_data.copy()

    if request.method == 'POST':
        # If the request is POST, instantiate the form with the submitted data
         # Use the correct form import
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
             # Use the correct ServiceBooking model import
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
                     # Use the correct CustomerMotorcycle model import
                    service_booking.vehicle = CustomerMotorcycle.objects.get(id=vehicle_id, owner=user)
                except CustomerMotorcycle.DoesNotExist: # Use the correct CustomerMotorcycle model import
                    # If the selected motorcycle is not found or doesn't belong to the user, show an error and go back to step 2
                    messages.error(request, "Selected motorcycle not found or does not belong to your account.")
                     # Redirect with service namespace and new URL name
                    return redirect(reverse('service:service_step2_authenticated'))
            else:
                 # If vehicle_id is missing from the session (should be set in step 2), redirect back to step 2
                 messages.error(request, "No vehicle selected for service.")
                  # Redirect with service namespace and new URL name
                 return redirect(reverse('service:service_step2_authenticated'))

            # Add service details from session
            try:
                service_type_id = booking_data.get('service_type_id')
                if service_type_id:
                    # Get the ServiceType instance using the ID from the session
                     # Use the correct ServiceType model import
                    service_booking.service_type = ServiceType.objects.get(id=service_type_id)
                else:
                    messages.error(request, "Invalid service type selected.")
                     # Redirect with service namespace and new URL name
                    return redirect(reverse('service:service_step1')) # Redirect to step 1


            except ServiceType.DoesNotExist: # Use the correct ServiceType model import
                # If the ServiceType ID from the session is invalid, redirect back to step 1
                messages.error(request, "Invalid service type selected.")
                 # Redirect with service namespace and new URL name
                return redirect(reverse('service:service_step1')) # Redirect to step 1


            # Convert the stored datetime string back to a datetime object
            if 'appointment_datetime_str' in booking_data:
                try:
                    service_booking.appointment_datetime = datetime.datetime.fromisoformat(
                        booking_data['appointment_datetime_str'])
                except (ValueError, TypeError):
                    # If the stored datetime string is invalid, show an error and go back to step 1
                    messages.error(request, "Invalid appointment date/time. Please select again.")
                     # Redirect with service namespace and new URL name
                    return redirect(reverse('service:service_step1')) # Redirect to step 1

            else:
                 # If appointment_datetime_str is missing, redirect back to step 1
                 messages.error(request, "Appointment date/time is missing.")
                  # Redirect with service namespace and new URL name
                 return redirect(reverse('service:service_step1')) # Redirect to step 1


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
                 # Redirect with service namespace and new URL name
                return redirect(reverse('service:service_confirmed')) # Updated URL name

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
                 # Template path updated to 'service/...'
                return render(request, 'service/service_user_details_authenticated.html', context)

        else: # If the form is NOT valid on POST
             # Add a general error message indicating form errors
             messages.error(request, "Please correct the errors below.")
             # The invalid form instance, containing field-specific errors, is automatically
             # passed to the template for rendering.

    else: # GET request (User arriving at this step for the first time or returning from subsequent step)
        # Instantiate the form. Django will use the 'initial' data provided.
        initial_data = booking_data.copy()

        # Pre-fill core contact fields from the user's profile, overriding any session data
        user = request.user # Ensure user is fetched for GET as well
        initial_data['first_name'] = user.first_name
        initial_data['last_name'] = user.last_name
        initial_data['email'] = user.email
        initial_data['phone_number'] = getattr(user, 'phone_number', '')
        # Preferred contact and comments are pre-filled from the session data (initial_data) if available

        # Use the correct form import
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
    # Template path updated to 'service/...'
    return render(request, 'service/service_user_details_authenticated.html', context)


# Step 3: Personal Information - Anonymous
# Renamed function
def booking_step3_anonymous(request):
    settings = SiteSettings.get_settings()
    if not settings.enable_service_booking:
        messages.error(request, "Service booking is currently disabled.")
        # Redirect to the core index view (no namespace needed)
        return redirect(reverse('index'))
    if not settings.allow_anonymous_bookings:
         messages.error(request, "Anonymous bookings are not allowed.")
         # Redirect with service namespace and new URL name
         return redirect(reverse('service:service_start'))

    # Retrieve data from previous steps
    booking_data = request.session.get(SERVICE_BOOKING_SESSION_KEY)
    if not booking_data:
        messages.warning(request, "Please start the booking process again.")
        # Redirect with service namespace and new URL name
        return redirect(reverse('service:service_step1'))


    if request.method == 'POST':
         # Use the correct form import
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
             # Use the correct ServiceBooking model import
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
                     # Use the correct ServiceType model import
                    service_booking.service_type = ServiceType.objects.get(id=service_type_id)
                else:
                    messages.error(request, "Invalid service type selected.")
                     # Redirect with service namespace and new URL name
                    return redirect(reverse('service:service_step1')) # Redirect to step 1
            except ServiceType.DoesNotExist: # Use the correct ServiceType model import
                messages.error(request, "Invalid service type selected.")
                 # Redirect with service namespace and new URL name
                return redirect(reverse('service:service_step1')) # Redirect to step 1


            # Convert the stored datetime string back to a datetime object
            if 'appointment_datetime_str' in booking_data:
                try:
                    service_booking.appointment_datetime = datetime.datetime.fromisoformat(
                        booking_data['appointment_datetime_str'])
                except (ValueError, TypeError):
                    messages.error(request, "Invalid appointment date/time. Please select again.")
                     # Redirect with service namespace and new URL name
                    return redirect(reverse('service:service_step1')) # Redirect to step 1


            service_booking.preferred_contact = booking_data.get('preferred_contact')
            service_booking.customer_notes = booking_data.get('booking_comments')

            service_booking.status = 'pending'

            try:
                service_booking.save()

                if SERVICE_BOOKING_SESSION_KEY in request.session:
                    del request.session[SERVICE_BOOKING_SESSION_KEY]
                request.session.modified = True

                messages.success(request, "Your service booking request has been submitted successfully.")
                 # Redirect with service namespace and new URL name
                return redirect(reverse('service:service_confirmed')) # Updated URL name

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
                 # Template path updated to 'service/...'
                return render(request, 'service/service_user_details_anonymous.html', context)

    else: # GET request
        initial_data = booking_data.copy()
        # Use the correct form import
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
    # Template path updated to 'service/...'
    return render(request, 'service/service_user_details_anonymous.html', context)


# Keep the confirmation view as is
# Renamed function
def service_confirmed_view(request): # Renamed function
    # Template path updated to 'service/...'
    return render(request, 'service/service_not_yet_confirmed.html')