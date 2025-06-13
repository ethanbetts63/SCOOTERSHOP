# inventory/views/user_views/step1_sales_profile.py

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.db import transaction
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin # Optional: if you want to enforce login

from inventory.models import TempSalesBooking, SalesProfile, InventorySettings
from inventory.forms import SalesProfileForm # Make sure to import your SalesProfileForm

class Step1SalesProfileView(View):
    """
    This view handles Step 1 of the user flow:
    Collecting customer personal details using the SalesProfileForm.
    """
    template_name = 'inventory/step1_sales_profile.html' # New template for this step

    def get(self, request, *args, **kwargs):
        # 1. Retrieve current_temp_booking_id from session
        temp_booking_id = request.session.get('current_temp_booking_id')
        if not temp_booking_id:
            messages.error(request, "Your booking session has expired or is invalid. Please start again.")
            return redirect(reverse('inventory:all')) # Redirect to motorcycle list or home

        # 2. Fetch TempSalesBooking instance
        temp_booking = get_object_or_404(TempSalesBooking, pk=temp_booking_id)

        # 3. Fetch InventorySettings (singleton)
        inventory_settings = InventorySettings.objects.first()
        if not inventory_settings:
            messages.error(request, "Inventory settings are not configured. Please contact support.")
            return redirect(reverse('inventory:all'))

        # 4. Initialize SalesProfileForm
        # Try to prefill SalesProfileForm if the user is logged in and has an existing profile
        sales_profile_instance = None
        if request.user.is_authenticated and hasattr(request.user, 'sales_profile'):
            sales_profile_instance = request.user.sales_profile
        # If a sales_profile is already linked to the temp_booking, use that instance for prefill
        elif temp_booking.sales_profile:
            sales_profile_instance = temp_booking.sales_profile

        sales_profile_form = SalesProfileForm(
            instance=sales_profile_instance,
            inventory_settings=inventory_settings,
            user=request.user # Pass user for prefilling logic in form's __init__
        )

        context = {
            'sales_profile_form': sales_profile_form,
            'temp_booking': temp_booking,
            'inventory_settings': inventory_settings,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        # 1. Retrieve current_temp_booking_id from session
        temp_booking_id = request.session.get('current_temp_booking_id')
        if not temp_booking_id:
            messages.error(request, "Your booking session has expired or is invalid. Please start again.")
            return redirect(reverse('inventory:all'))

        # 2. Fetch TempSalesBooking instance
        temp_booking = get_object_or_404(TempSalesBooking, pk=temp_booking_id)

        # 3. Fetch InventorySettings
        inventory_settings = InventorySettings.objects.first()
        if not inventory_settings:
            messages.error(request, "Inventory settings are not configured. Please contact support.")
            return redirect(reverse('inventory:all'))

        # 4. Initialize SalesProfileForm with POST data
        sales_profile_instance = None
        if request.user.is_authenticated and hasattr(request.user, 'sales_profile'):
            sales_profile_instance = request.user.sales_profile
        elif temp_booking.sales_profile:
            sales_profile_instance = temp_booking.sales_profile

        sales_profile_form = SalesProfileForm(
            request.POST,
            request.FILES, # Important for drivers_license_image
            instance=sales_profile_instance,
            inventory_settings=inventory_settings,
            user=request.user
        )

        # 5. Validate the form
        if sales_profile_form.is_valid():
            with transaction.atomic():
                # Save/Update SalesProfile
                sales_profile = sales_profile_form.save(commit=False)
                if request.user.is_authenticated and not sales_profile.user:
                    sales_profile.user = request.user # Link to user if not already linked
                sales_profile.save()

                # Link the saved SalesProfile to the current TempSalesBooking
                temp_booking.sales_profile = sales_profile
                temp_booking.save()

                messages.success(request, "Personal details saved. Proceed to booking details and appointment.")
                # Redirect to the next step: Booking Details and Appointment
                return redirect(reverse('inventory:booking_details_and_appointment'))
        else:
            # Form is invalid, re-render the template with errors
            context = {
                'sales_profile_form': sales_profile_form,
                'temp_booking': temp_booking,
                'inventory_settings': inventory_settings,
            }
            messages.error(request, "Please correct the errors below.")
            return render(request, self.template_name, context)

