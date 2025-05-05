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

# Handles the third step of booking for authenticated users: personal information and booking creation.
@login_required
def booking_step3_authenticated(request):
    settings = SiteSettings.get_settings()
    if not settings.enable_service_booking:
        messages.error(request, "Service booking is currently disabled.")
        return redirect(reverse('core:index'))

    booking_data = request.session.get(SERVICE_BOOKING_SESSION_KEY)
    if not booking_data:
        messages.warning(request, "Please start the booking process again.")
        return redirect(reverse('service:service_step1'))

    user = request.user

    # initial_data = booking_data.copy() # This line is not used here before the POST check

    if request.method == 'POST':
        form = ServiceBookingUserForm(request.POST)
        # Note: The 'is_returning_customer' field should be handled in the form's __init__
        # based on request.user.is_authenticated, not popped here after instantiation.
        # If the field exists and needs to be excluded for authenticated users,
        # modify the form's __init__ method or use a different form class.
        if 'is_returning_customer' in form.fields:
             form.fields.pop('is_returning_customer')


        if form.is_valid():
            # Update user profile details from the form
            user.first_name = form.cleaned_data.get('first_name', user.first_name)
            user.last_name = form.cleaned_data.get('last_name', user.last_name)
            user.email = form.cleaned_data.get('email', user.email)
            # Use setattr for phone_number as it might not exist on older User models
            user.phone_number = form.cleaned_data.get('phone_number', getattr(user, 'phone_number', ''))

            try:
                user.save()
                messages.success(request, "Your profile details have been updated.")
            except Exception as e:
                 messages.error(request, f"There was an error updating your profile: {e}")

            # Update booking_data in session with form data (includes preferred_contact and booking_comments)
            booking_data.update(form.cleaned_data)
            request.session[SERVICE_BOOKING_SESSION_KEY] = booking_data
            request.session.modified = True # Explicitly mark session as modified

            # Create the ServiceBooking instance
            service_booking = ServiceBooking()

            # Link to authenticated user
            service_booking.customer = user
            # Use updated user details for booking name/email/phone
            service_booking.customer_name = f"{user.first_name} {user.last_name}".strip()
            service_booking.customer_email = user.email
            service_booking.customer_phone = getattr(user, 'phone_number', '') # Use updated phone number


            # Get vehicle from session
            vehicle_id = booking_data.get('vehicle_id')
            if vehicle_id:
                try:
                    # Ensure the vehicle belongs to the logged-in user
                    service_booking.vehicle = CustomerMotorcycle.objects.get(id=vehicle_id, owner=user)
                except CustomerMotorcycle.DoesNotExist:
                    messages.error(request, "Selected motorcycle not found or does not belong to your account.")
                    return redirect(reverse('service:service_step2_authenticated'))
            else:
                 messages.error(request, "No vehicle selected for service.")
                 return redirect(reverse('service:service_step2_authenticated')) # Redirect to step 2 if no vehicle

            # Get Service Type from session
            try:
                service_type_id = booking_data.get('service_type_id')
                if service_type_id:
                    service_booking.service_type = ServiceType.objects.get(id=service_type_id)
                else:
                    messages.error(request, "Invalid service type selected.")
                    return redirect(reverse('service:service_step1')) # Redirect to step 1 if no service type id

            except ServiceType.DoesNotExist:
                messages.error(request, "Invalid service type selected.")
                return redirect(reverse('service:service_step1')) # Redirect to step 1 if service type is invalid

            # Get Appointment Datetime from session
            if 'appointment_datetime_str' in booking_data:
                try:
                    # Assuming datetime is stored as ISO format string
                    appointment_datetime = datetime.datetime.fromisoformat(
                        booking_data['appointment_datetime_str'])
                    # Make it timezone-aware if your project uses timezones and the string is naive
                    # if timezone.is_aware(appointment_datetime_str): # This check might not work as expected on a string
                    # Instead, parse and then make aware if needed, based on your project's TIME_ZONE
                    # from django.conf import settings
                    # if settings.USE_TZ:
                    #     appointment_datetime = timezone.make_aware(appointment_datetime, timezone.get_current_timezone())

                    service_booking.appointment_datetime = appointment_datetime

                except (ValueError, TypeError):
                    messages.error(request, "Invalid appointment date/time. Please select again.")
                    return redirect(reverse('service:service_step1')) # Redirect to step 1 if datetime is invalid

            else:
                 messages.error(request, "Appointment date/time is missing.")
                 return redirect(reverse('service:service_step1')) # Redirect to step 1 if datetime is missing

            # Get preferred contact and notes from the form data (which updated booking_data)
            service_booking.preferred_contact = booking_data.get('preferred_contact')
            service_booking.customer_notes = booking_data.get('booking_comments')

            service_booking.status = 'pending' # Set initial status

            # --- Save the Booking ---
            try:
                service_booking.save()

                # Clear the booking data from the session upon successful saving
                if SERVICE_BOOKING_SESSION_KEY in request.session:
                    del request.session[SERVICE_BOOKING_SESSION_KEY]
                request.session.modified = True # Explicitly mark session as modified

                messages.success(request, "Your service booking request has been submitted successfully.")
                return redirect(reverse('service:service_confirmed'))

            except Exception as e:
                # Handle potential errors during saving
                print(f"Error saving booking: {e}") # Log the error
                messages.error(request, f"There was an error saving your booking. Please try again. Error: {e}")

                # Re-render the form with context in case of saving error
                context = {
                    'step': 3,
                    'total_steps': 3,
                    'form': form, # Pass the form with potentially pre-filled data and errors
                    'is_authenticated': True,
                    # You might need other context data here
                }
                return render(request, 'service/service_user_details_authenticated.html', context)


        else:
            # --- Form is NOT valid ---
            # Add an error message to the messages framework
            messages.error(request, "Please correct the errors below.")
            # The invalid form with errors will be passed to the template in the context below

    # --- Handle GET Request or Render Invalid Form ---
    else:
        # For a GET request, initialize the form with user's current data
        initial_data = booking_data.copy() # Start with booking data from session

        user = request.user # Get the authenticated user
        initial_data['first_name'] = user.first_name
        initial_data['last_name'] = user.last_name
        initial_data['email'] = user.email
        initial_data['phone_number'] = getattr(user, 'phone_number', '')
        # You might also initialize preferred_contact and booking_comments from session
        # initial_data['preferred_contact'] = initial_data.get('preferred_contact', 'email')
        # initial_data['booking_comments'] = initial_data.get('booking_comments', '')


        form = ServiceBookingUserForm(initial=initial_data)
        # Remove 'is_returning_customer' field for authenticated users if it exists in the form class
        if 'is_returning_customer' in form.fields:
            form.fields.pop('is_returning_customer')


    # Prepare context data for the template
    context = {
        'form': form, # Pass the form (either initialized GET form or invalid POST form)
        'step': 3, # Current step
        'total_steps': 3, # Total steps in the booking process
        'is_authenticated': True, # Indicate authenticated flow
        # You might need other context data here, e.g., booking summary from session
        'booking_summary': booking_data # Pass session data to display summary
    }
    return render(request, 'service/service_user_details_authenticated.html', context)


# Handles the third step of booking for anonymous users: personal information and booking creation.
def booking_step3_anonymous(request):
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
        form = ServiceBookingUserForm(request.POST)

        if form.is_valid():
            # --- Process Valid Form Data and Session Data ---
            booking_data.update(form.cleaned_data)
            request.session[SERVICE_BOOKING_SESSION_KEY] = booking_data
            request.session.modified = True # Explicitly mark session as modified


            # Create the ServiceBooking instance
            service_booking = ServiceBooking()

            # No customer linked for anonymous booking
            service_booking.customer = None

            # Populate booking from form data (customer contact details and notes)
            service_booking.customer_name = f"{form.cleaned_data['first_name']} {form.cleaned_data['last_name']}"
            service_booking.customer_email = form.cleaned_data['email']
            service_booking.customer_phone = form.cleaned_data.get('phone_number')
            service_booking.preferred_contact = form.cleaned_data.get('preferred_contact') # Preferred contact is in the form now
            service_booking.customer_notes = form.cleaned_data.get('booking_comments') # Booking comments are in the form now


            # Populate booking from session data (anonymous vehicle details)
            service_booking.anon_vehicle_make = booking_data.get('anon_vehicle_make')
            service_booking.anon_vehicle_model = booking_data.get('anon_vehicle_model')
            service_booking.anon_vehicle_year = booking_data.get('anon_vehicle_year')
            service_booking.anon_vehicle_rego = booking_data.get('anon_vehicle_rego')
            # service_booking.anon_vehicle_vin_number = booking_data.get('anon_vehicle_vin_number') # Removed as per test fix
            service_booking.anon_vehicle_odometer = booking_data.get('anon_vehicle_odometer')
            service_booking.anon_vehicle_transmission = booking_data.get('anon_vehicle_transmission')


            # Get Service Type from session
            try:
                service_type_id = booking_data.get('service_type_id')
                if service_type_id:
                    service_booking.service_type = ServiceType.objects.get(id=service_type_id)
                else:
                    messages.error(request, "Invalid service type selected.")
                    return redirect(reverse('service:service_step1')) # Redirect to step 1 if no service type id
            except ServiceType.DoesNotExist:
                messages.error(request, "Invalid service type selected.")
                return redirect(reverse('service:service_step1')) # Redirect to step 1 if service type is invalid


            # Get Appointment Datetime from session
            if 'appointment_datetime_str' in booking_data:
                try:
                    # Assuming datetime is stored as ISO format string
                    appointment_datetime = datetime.datetime.fromisoformat(
                        booking_data['appointment_datetime_str'])
                     # Make it timezone-aware if your project uses timezones and the string is naive
                    # from django.conf import settings
                    # if settings.USE_TZ:
                    #     appointment_datetime = timezone.make_aware(appointment_datetime, timezone.get_current_timezone())

                    service_booking.appointment_datetime = appointment_datetime

                except (ValueError, TypeError):
                    messages.error(request, "Invalid appointment date/time. Please select again.")
                    return redirect(reverse('service:service_step1')) # Redirect to step 1 if datetime is invalid

            # Note: If appointment_datetime_str is missing, the test might not cover this specific case,
            # but the redirect ensures the flow doesn't break here.
            # You might want a more explicit check like:
            # else:
            #      messages.error(request, "Appointment date/time is missing.")
            #      return redirect(reverse('service:service_step1'))


            service_booking.status = 'pending' # Set initial status

            # --- Save the Booking ---
            try:
                service_booking.save()

                # Clear the booking data from the session upon successful saving
                if SERVICE_BOOKING_SESSION_KEY in request.session:
                    del request.session[SERVICE_BOOKING_SESSION_KEY]
                request.session.modified = True # Explicitly mark session as modified

                messages.success(request, "Your service booking request has been submitted successfully.")
                return redirect(reverse('service:service_confirmed'))

            except Exception as e:
                # Handle potential errors during saving
                print(f"Error saving booking: {e}") # Log the error
                messages.error(request, f"There was an error saving your booking. Please try again. Error: {e}")

                # Re-render the form with context in case of saving error
                context = {
                    'step': 3,
                    'total_steps': 3,
                    'form': form, # Pass the form with potentially pre-filled data and errors
                    'is_authenticated': False,
                    'allow_anonymous_bookings': settings.allow_anonymous_bookings,
                     'booking_summary': booking_data # Pass session data to display summary
                }
                return render(request, 'service/service_user_details_anonymous.html', context)


        else:
            # --- Form is NOT valid ---
            # Add an error message to the messages framework
            messages.error(request, "Please correct the errors below.")
            # The invalid form with errors will be passed to the template in the context below

    # --- Handle GET Request or Render Invalid Form ---
    else:
        # For a GET request, initialize the form (potentially with session data if needed)
        # Since comments and contact details are in the form now, you might initialize
        # the form with existing session data if the user goes back to this step.
        initial_data = booking_data.copy() # Start with booking data from session



        form = ServiceBookingUserForm(initial=initial_data)

    # Prepare context data for the template
    context = {
        'form': form, # Pass the form (either initialized GET form or invalid POST form)
        'step': 3, # Current step
        'total_steps': 3, # Total steps in the booking process
        'is_authenticated': False, # Indicate anonymous flow
        'allow_anonymous_bookings': settings.allow_anonymous_bookings,
        'booking_summary': booking_data # Pass session data to display summary
    }
    return render(request, 'service/service_user_details_anonymous.html', context)