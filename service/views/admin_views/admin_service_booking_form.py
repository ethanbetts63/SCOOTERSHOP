from django.views.generic import View
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from service.models import ServiceProfile, CustomerMotorcycle, ServiceBooking, ServiceType
from service.forms import AdminBookingDetailsForm
from service.utils.admin_create_service_booking import admin_create_service_booking

class AdminBookingCreateView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    Simplified view for administrators to create a new Service Booking.
    This view handles the selection of an existing ServiceProfile and CustomerMotorcycle,
    followed by entering the booking details.
    """
    template_name = 'service/admin_service_booking_form.html'

    def test_func(self):
        """
        Ensures that only staff or superusers can access this view.
        """
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        """
        Prepares and returns the context dictionary for the template.
        """
        context = {
            'booking_details_form': kwargs.get('booking_details_form'),
            'selected_profile': kwargs.get('selected_profile'),
            'selected_motorcycle': kwargs.get('selected_motorcycle'),
            'ajax_search_customer_url': reverse_lazy('service:admin_api_search_customer'),
            'admin_api_get_customer_details': reverse('service:admin_api_get_customer_details', kwargs={'profile_id': 0}),
            'ajax_get_customer_motorcycles_url': reverse('service:admin_api_customer_motorcycles', kwargs={'profile_id': 0}),
            'ajax_get_motorcycle_details_url': reverse('service:admin_api_get_motorcycle_details', kwargs={'motorcycle_id': 0}),
            'create_profile_url': reverse_lazy('service:admin_create_service_profile'),
            'create_motorcycle_url': reverse_lazy('service:admin_create_customer_motorcycle'),
        }
        return context

    def get(self, request, *args, **kwargs):
        """
        Handles GET requests, displaying the initial state of the booking form.
        """
        booking_details_form = AdminBookingDetailsForm()
        context = self.get_context_data(booking_details_form=booking_details_form)
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests, processing form submissions and creating the booking.
        """
        selected_profile_id = request.POST.get('selected_profile_id')
        selected_motorcycle_id = request.POST.get('selected_motorcycle_id')

        service_profile = None
        customer_motorcycle = None
        
        # --- Stage 1: Validate Selections ---
        if not selected_profile_id:
            messages.error(request, "A customer profile must be selected.")
        else:
            service_profile = get_object_or_404(ServiceProfile, pk=selected_profile_id)

        if not selected_motorcycle_id:
            messages.error(request, "A customer motorcycle must be selected.")
        else:
            customer_motorcycle = get_object_or_404(CustomerMotorcycle, pk=selected_motorcycle_id)
        
        if service_profile and customer_motorcycle and customer_motorcycle.service_profile != service_profile:
            messages.error(request, "The selected motorcycle does not belong to the selected customer profile.")
            customer_motorcycle = None

        # --- Stage 2: Process Booking Details ---
        booking_details_form = AdminBookingDetailsForm(request.POST)

        if service_profile and customer_motorcycle:
            if booking_details_form.is_valid():
                # Add any non-blocking warnings from the form to the messages framework.
                if hasattr(booking_details_form, 'get_warnings'):
                    for warning in booking_details_form.get_warnings():
                        messages.warning(request, warning)
                
                try:
                    booking = admin_create_service_booking(
                        admin_booking_form_data=booking_details_form.cleaned_data,
                        service_profile=service_profile,
                        customer_motorcycle=customer_motorcycle
                    )
                    messages.success(request, f"Booking {booking.service_booking_reference} created successfully!")
                    return redirect(reverse_lazy('service:service_booking_management'))
                except Exception as e:
                    messages.error(request, f"An unexpected error occurred while creating the booking: {e}")
            else:
                 for field, error_list in booking_details_form.errors.items():
                    for error in error_list:
                        messages.error(request, f"Error in '{booking_details_form[field].label}': {error}")
        
        # --- Re-render on failure ---
        context = self.get_context_data(
            booking_details_form=booking_details_form,
            selected_profile=service_profile,
            selected_motorcycle=customer_motorcycle
        )
        return render(request, self.template_name, context)
