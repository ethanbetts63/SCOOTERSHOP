from django.views.generic import View
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.contrib import messages
from service.mixins import AdminRequiredMixin
from service.models import ServiceProfile, CustomerMotorcycle, ServiceBooking
from service.forms import AdminBookingDetailsForm
from service.utils.admin_create_service_booking import admin_create_service_booking


class AdminServiceBookingCreateUpdateView(AdminRequiredMixin, View):
    template_name = "service/admin_service_booking_create_update.html"

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = {
            "ajax_search_customer_url": reverse_lazy(
                "service:admin_api_search_customer"
            ),
            "create_profile_url": reverse_lazy("service:admin_create_service_profile"),
            "create_motorcycle_url": reverse_lazy(
                "service:admin_create_customer_motorcycle"
            ),
        }

        context.update(kwargs)
        return context

    def get(self, request, pk=None, *args, **kwargs):
        if pk:
            booking = get_object_or_404(ServiceBooking, pk=pk)
            booking_details_form = AdminBookingDetailsForm(instance=booking)
            selected_profile = booking.service_profile
            selected_motorcycle = booking.customer_motorcycle
            context = self.get_context_data(
                booking_details_form=booking_details_form,
                selected_profile=selected_profile,
                selected_motorcycle=selected_motorcycle,
                instance=booking,
            )
        else:
            booking_details_form = AdminBookingDetailsForm()
            context = self.get_context_data(
                booking_details_form=booking_details_form,
                selected_profile=None,
                selected_motorcycle=None,
                instance=None,
            )
        return render(request, self.template_name, context)

    def post(self, request, pk=None, *args, **kwargs):
        booking_instance = None
        if pk:
            booking_instance = get_object_or_404(ServiceBooking, pk=pk)

            service_profile = booking_instance.service_profile
            customer_motorcycle = booking_instance.customer_motorcycle
        else:
            selected_profile_id = request.POST.get("selected_profile_id")
            selected_motorcycle_id = request.POST.get("selected_motorcycle_id")

            service_profile = (
                get_object_or_404(ServiceProfile, pk=selected_profile_id)
                if selected_profile_id
                else None
            )
            customer_motorcycle = (
                get_object_or_404(CustomerMotorcycle, pk=selected_motorcycle_id)
                if selected_motorcycle_id
                else None
            )

            if not service_profile or not customer_motorcycle:
                messages.error(
                    request, "A customer profile and motorcycle must be selected."
                )
            elif customer_motorcycle.service_profile != service_profile:
                messages.error(
                    request,
                    "The selected motorcycle does not belong to the selected customer profile.",
                )
                customer_motorcycle = None

        booking_details_form = AdminBookingDetailsForm(
            request.POST, instance=booking_instance
        )

        if service_profile and customer_motorcycle and booking_details_form.is_valid():
            if pk:
                booking_details_form.save()
                messages.success(
                    request,
                    f"Booking {booking_instance.service_booking_reference} updated successfully!",
                )
            else:
                try:
                    booking = admin_create_service_booking(
                        admin_booking_form_data=booking_details_form.cleaned_data,
                        service_profile=service_profile,
                        customer_motorcycle=customer_motorcycle,
                    )
                    messages.success(
                        request,
                        f"Booking {booking.service_booking_reference} created successfully!",
                    )
                except Exception as e:
                    messages.error(request, f"An unexpected error occurred: {e}")

                    context = self.get_context_data(
                        booking_details_form=booking_details_form,
                        selected_profile=service_profile,
                        selected_motorcycle=customer_motorcycle,
                        instance=booking_instance,
                    )
                    return render(request, self.template_name, context)

            return redirect(reverse_lazy("service:service_booking_management"))

        if not (service_profile and customer_motorcycle):
            messages.error(request, "Please select a valid customer and motorcycle.")

        for field, error_list in booking_details_form.errors.items():
            for error in error_list:
                messages.error(
                    request,
                    f"Error in '{booking_details_form.fields[field].label}': {error}",
                )

        context = self.get_context_data(
            booking_details_form=booking_details_form,
            selected_profile=service_profile,
            selected_motorcycle=customer_motorcycle,
            instance=booking_instance,
        )
        return render(request, self.template_name, context)
