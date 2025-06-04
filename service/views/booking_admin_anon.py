# service/views/booking_admin_anon.py

# from django.shortcuts import render, redirect
# from django.contrib.auth.decorators import user_passes_test
# from django.contrib import messages
# from django.urls import reverse

# from service.forms import AdminAnonBookingForm
# from service.models import ServiceBooking, ServiceType

# # Checks if the user is staff or a superuser
# def is_staff_or_superuser(user):
#     return user.is_active and (user.is_staff or user.is_superuser)

# # Handles admin booking for anonymous users
# @user_passes_test(is_staff_or_superuser)
# def booking_admin_anon_view(request):
#     if request.method == 'POST':
#         # Initializes form with POST data
#         form = AdminAnonBookingForm(request.POST)
#         if form.is_valid():
#             # Extracts customer details from form
#             first_name = form.cleaned_data['one_off_first_name']
#             last_name = form.cleaned_data['one_off_last_name']
#             email = form.cleaned_data.get('one_off_email', '')
#             phone_number = form.cleaned_data.get('one_off_phone_number', '')
#             customer_address = form.cleaned_data.get('anon_customer_address', '')

#             # Extracts vehicle details from form
#             anon_vehicle_make = form.cleaned_data.get('anon_vehicle_make')
#             anon_vehicle_model = form.cleaned_data.get('anon_vehicle_model')
#             anon_vehicle_year = form.cleaned_data.get('anon_vehicle_year')
#             anon_vehicle_rego = form.cleaned_data.get('anon_vehicle_rego', '')
#             anon_vehicle_vin_number = form.cleaned_data.get('anon_vehicle_vin_number', '') # Added anon_vehicle_vin_number
#             anon_vehicle_odometer = form.cleaned_data.get('anon_vehicle_odometer')
#             anon_vehicle_transmission = form.cleaned_data.get('anon_vehicle_transmission', '')
#             anon_engine_number = form.cleaned_data.get('anon_engine_number', '')

#             # Extracts service details from form
#             service_type = form.cleaned_data['service_type']
#             appointment_date = form.cleaned_data['appointment_date']
#             # Removed preferred_contact
#             booking_comments = form.cleaned_data.get('booking_comments', '')

#             # Creates a new ServiceBooking instance
#             booking = ServiceBooking(
#                 customer=None,
#                 customer_name=f"{first_name} {last_name}",
#                 customer_email=email,
#                 customer_phone=phone_number,
#                 customer_address=customer_address,

#                 anon_vehicle_make=anon_vehicle_make,
#                 anon_vehicle_model=anon_vehicle_model,
#                 anon_vehicle_year=anon_vehicle_year,
#                 anon_vehicle_rego=anon_vehicle_rego,
#                 anon_vehicle_vin_number=anon_vehicle_vin_number, # Added anon_vehicle_vin_number
#                 anon_vehicle_odometer=anon_vehicle_odometer,
#                 anon_vehicle_transmission=anon_vehicle_transmission,
#                 anon_engine_number=anon_engine_number,

#                 vehicle=None,

#                 service_type=service_type,
#                 appointment_date=appointment_date,
#                 customer_notes=booking_comments,
#                 status='pending',
#             )
#             # Saves the booking to the database
#             booking.save()

#             # Displays success message
#             messages.success(request, f"One-off service booking created successfully for {first_name} {last_name}.")
#             # Redirects to the same view
#             return redirect(reverse('service:admin_booking_anon'))

#         else:
#             # Displays error message for invalid form
#             messages.error(request, "Please correct the errors below.")

#     else:
#         # Initializes an empty form for GET requests
#         form = AdminAnonBookingForm()

#     # Prepares context for rendering the template
#     context = {
#         'page_title': 'Admin Service Booking for Anonymous/One-off Customer',
#         'form': form,
#     }
#     # Renders the booking template
#     return render(request, 'service/service_booking_admin_anon.html', context)