# SCOOTER_SHOP/inventory/views/admin_views/sales_booking_create_update_view.py

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.contrib import messages
from inventory.mixins import AdminRequiredMixin

from inventory.forms import AdminSalesBookingForm
from inventory.models import SalesBooking

class SalesBookingCreateUpdateView(AdminRequiredMixin, View):
    template_name = 'inventory/admin_sales_booking_create_update.html'
    form_class = AdminSalesBookingForm

    def get(self, request, pk=None, *args, **kwargs):
        instance = None
        if pk:
            instance = get_object_or_404(SalesBooking, pk=pk)
            # When initializing the form for GET (edit mode),
            # we want to pass the instance so the form's __init__ can
            # set the initial values for the hidden selected_profile_id and selected_motorcycle_id.
            form = self.form_class(instance=instance)
        else:
            # For create mode, no instance is passed.
            form = self.form_class()

        context = {
            'form': form,
            'is_edit_mode': bool(pk),
            'current_booking': instance, # This will be the SalesBooking instance if in edit mode
            'page_title': "Edit Sales Booking" if pk else "Create Sales Booking"
        }
        return render(request, self.template_name, context)

    def post(self, request, pk=None, *args, **kwargs):
        instance = None
        if pk:
            instance = get_object_or_404(SalesBooking, pk=pk)
            form = self.form_class(request.POST, instance=instance)
        else:
            form = self.form_class(request.POST)

        if form.is_valid():
            # Save the form but do NOT commit to the database yet.
            # This gives us the SalesBooking instance (either new or existing)
            # without saving the FKs that are not in Meta.fields.
            sales_booking = form.save(commit=False)

            # Manually assign the foreign key relationships (SalesProfile and Motorcycle)
            # which were fetched and stored in form.cleaned_data by the form's clean() method.
            sales_booking.sales_profile = form.cleaned_data['sales_profile']
            sales_booking.motorcycle = form.cleaned_data['motorcycle']
            
            # Now, save the instance to the database.
            # This will create or update the SalesBooking record with the correctly linked FKs.
            sales_booking.save()

            if pk:
                messages.success(request, f"Sales Booking '{sales_booking.sales_booking_reference}' updated successfully.")
            else:
                messages.success(request, f"Sales Booking '{sales_booking.sales_booking_reference}' created successfully.")
            return redirect(reverse('inventory:sales_bookings_management'))
        else:
            messages.error(request, "Please correct the errors below.")
            context = {
                'form': form,
                'is_edit_mode': bool(pk),
                'current_booking': instance, # Still need to pass the original instance for context if in edit mode
                'page_title': "Edit Sales Booking" if pk else "Create Sales Booking"
            }
            return render(request, self.template_name, context)

