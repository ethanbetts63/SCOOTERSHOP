from django.views.generic import View
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from service.models import ServiceProfile, CustomerMotorcycle, ServiceType
from service.forms import AdminServiceProfileForm, AdminCustomerMotorcycleForm, AdminBookingDetailsForm
from service.utils.admin_parse_booking_request_flags import admin_parse_booking_request_flags
from service.utils.admin_process_service_profile_form import admin_process_service_profile_form
from service.utils.admin_process_customer_motorcycle_form import admin_process_customer_motorcycle_form
from service.utils.admin_create_service_booking import admin_create_service_booking

class AdminBookingCreateView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    Unified view for administrators to create a new Service Booking.
    This view handles the selection/creation of a ServiceProfile,
    selection/creation of a CustomerMotorcycle, and finally the
    input of booking details to create a ServiceBooking.
    """
    template_name = 'service/admin_service_booking_form.html' 

    def test_func(self):
        """
        Ensures that only staff users can access this view.
        You might want to customize this further based on your permissions system.
        """
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_initial_forms(self, request, selected_profile=None, selected_motorcycle=None, booking_details_initial=None):
        """
        Initializes and returns instances of all three forms, pre-populating
        them if 'selected_profile' or 'selected_motorcycle' objects are provided.
        """
        profile_form = AdminServiceProfileForm(instance=selected_profile)
        motorcycle_form = AdminCustomerMotorcycleForm(instance=selected_motorcycle)
        booking_details_form = AdminBookingDetailsForm(initial=booking_details_initial)

        return profile_form, motorcycle_form, booking_details_form

    def get_context_data(self, **kwargs):
        """
        Prepares and returns the context dictionary for the template.
        This includes all forms, selected objects, and flags to control
        visibility of sections in the template.
        """
        context = {
            'profile_form': kwargs.get('profile_form'),
            'motorcycle_form': kwargs.get('motorcycle_form'),
            'booking_details_form': kwargs.get('booking_details_form'),
            'selected_profile': kwargs.get('selected_profile'),
            'selected_motorcycle': kwargs.get('selected_motorcycle'),
            'show_motorcycle_section': bool(kwargs.get('selected_profile')),
            'show_booking_details_section': bool(kwargs.get('selected_profile') and kwargs.get('selected_motorcycle')),
            'all_service_types': ServiceType.objects.filter(is_active=True).order_by('name'),
            'ajax_search_customer_url': reverse_lazy('service:admin_api_search_customer'),
            # FIX: Pass a dummy profile_id=0 to reverse_lazy as a placeholder for JavaScript
            'admin_api_get_customer_details': reverse_lazy('service:admin_api_get_customer_details', kwargs={'profile_id': 0}),
            # FIX: Pass a dummy profile_id=0 to reverse_lazy as a placeholder for JavaScript
            'ajax_get_customer_motorcycles_url': reverse_lazy('service:admin_api_customer_motorcycles', kwargs={'profile_id': 0}),
            # FIX: Pass a dummy motorcycle_id=0 to reverse_lazy as a placeholder for JavaScript
            'ajax_get_motorcycle_details_url': reverse_lazy('service:admin_api_get_motorcycle_details', kwargs={'motorcycle_id': 0}),
            'ajax_service_date_availability_url': reverse_lazy('service:admin_api_service_date_availability'),
            'ajax_dropoff_time_availability_url': reverse_lazy('service:admin_api_dropoff_time_availability'),
            'ajax_booking_precheck_url': reverse_lazy('service:admin_api_booking_precheck'),
        }
        # Add any warnings from the booking details form
        if context['booking_details_form'] and hasattr(context['booking_details_form'], 'get_warnings'):
            context['booking_warnings'] = context['booking_details_form'].get_warnings()
            for warning in context['booking_warnings']:
                messages.warning(self.request, warning)

        return context

    def get(self, request, *args, **kwargs):
        """
        Handles GET requests, displaying the initial state of the booking form.
        """
        profile_form, motorcycle_form, booking_details_form = self.get_initial_forms(request)
        context = self.get_context_data(
            profile_form=profile_form,
            motorcycle_form=motorcycle_form,
            booking_details_form=booking_details_form
        )
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests, processing form submissions and creating the booking.
        """
        # Parse hidden flags from the POST request
        flags = admin_parse_booking_request_flags(request.POST)
        selected_profile_id = flags['selected_profile_id']
        selected_motorcycle_id = flags['selected_motorcycle_id']
        create_new_profile = flags['create_new_profile']
        create_new_motorcycle = flags['create_new_motorcycle']

        service_profile_instance = None
        customer_motorcycle_instance = None
        booking_details_form = None # Initialize to None for consistent re-rendering

        # --- Stage 1: Process Service Profile ---
        profile_form_valid = False
        if create_new_profile or not selected_profile_id:
            profile_form, service_profile_instance = admin_process_service_profile_form(request.POST)
            if profile_form.is_valid():
                profile_form_valid = True
            else:
                messages.error(request, "Please correct errors in the Customer Profile section.")
        else:
            try:
                service_profile_instance = get_object_or_404(ServiceProfile, pk=selected_profile_id)
                # Re-initialize the form for display, potentially with its current instance
                profile_form = AdminServiceProfileForm(instance=service_profile_instance)
                profile_form_valid = True # Assume valid if object found
            except Exception:
                messages.error(request, "Selected Customer Profile not found or invalid.")
                profile_form = AdminServiceProfileForm(request.POST) # Re-bind to show original input if any
                service_profile_instance = None
                profile_form_valid = False

        # --- Stage 2: Process Customer Motorcycle (only if profile is valid) ---
        motorcycle_form_valid = False
        if service_profile_instance:
            if create_new_motorcycle or not selected_motorcycle_id:
                # Admin chose to create a new motorcycle or no motorcycle was pre-selected
                motorcycle_form, customer_motorcycle_instance = admin_process_customer_motorcycle_form(
                    request.POST, request.FILES, service_profile_instance # Pass profile_instance for new motorcycles
                )
                if motorcycle_form.is_valid():
                    motorcycle_form_valid = True
                else:
                    messages.error(request, "Please correct errors in the Customer Motorcycle section.")
            else:
                # An existing motorcycle was selected
                try:
                    customer_motorcycle_instance = get_object_or_404(CustomerMotorcycle, pk=selected_motorcycle_id)
                    # Ensure it's linked to the selected profile (important for security/data integrity)
                    if customer_motorcycle_instance.service_profile != service_profile_instance:
                        messages.error(request, "Selected motorcycle does not belong to the selected customer profile.")
                        customer_motorcycle_instance = None # Invalidate selection
                        motorcycle_form = AdminCustomerMotorcycleForm(request.POST, request.FILES)
                        motorcycle_form_valid = False
                    else:
                        motorcycle_form = AdminCustomerMotorcycleForm(instance=customer_motorcycle_instance)
                        motorcycle_form_valid = True
                except Exception:
                    messages.error(request, "Selected Customer Motorcycle not found or invalid.")
                    motorcycle_form = AdminCustomerMotorcycleForm(request.POST, request.FILES)
                    customer_motorcycle_instance = None
                    motorcycle_form_valid = False
        else:
            # If profile wasn't valid, motorcycle section cannot proceed.
            motorcycle_form = AdminCustomerMotorcycleForm(request.POST, request.FILES) # Re-bind for display

        # --- Stage 3: Process Booking Details (only if profile and motorcycle are valid) ---
        booking_created = False
        if service_profile_instance and customer_motorcycle_instance:
            booking_details_form = AdminBookingDetailsForm(request.POST)
            if booking_details_form.is_valid():
                try:
                    # Create the ServiceBooking instance
                    booking = admin_create_service_booking(
                        admin_booking_form_data=booking_details_form.cleaned_data,
                        service_profile=service_profile_instance,
                        customer_motorcycle=customer_motorcycle_instance
                    )
                    messages.success(request, f"Booking {booking.service_booking_reference} created successfully!")
                    booking_created = True
                    # Redirect to a success page or the booking management list
                    return redirect(reverse_lazy('service:service_booking_management'))
                except Exception as e:
                    messages.error(request, f"Error creating booking: {e}")
                    # Re-render the form with error
            else:
                messages.error(request, "Please correct errors in the Booking Details section.")
        else:
            # If profile or motorcycle not valid, re-bind booking details form for display
            booking_details_form = AdminBookingDetailsForm(request.POST)

        if not profile_form_valid:
            motorcycle_form = AdminCustomerMotorcycleForm(request.POST, request.FILES)
            booking_details_form = AdminBookingDetailsForm(request.POST)
        elif not motorcycle_form_valid:
            booking_details_form = AdminBookingDetailsForm(request.POST)

        context = self.get_context_data(
            profile_form=profile_form,
            motorcycle_form=motorcycle_form,
            booking_details_form=booking_details_form,
            selected_profile=service_profile_instance,
            selected_motorcycle=customer_motorcycle_instance
        )
        return render(request, self.template_name, context)
