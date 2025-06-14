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
        # 1. Retrieve temp_sales_booking_uuid from session.
        # This now expects the UUID string stored by initiate_booking_process_view.
        temp_booking_uuid = request.session.get('temp_sales_booking_uuid')
        print(f"DEBUG (Step1 GET): Retrieved 'temp_sales_booking_uuid': {temp_booking_uuid}")

        if not temp_booking_uuid:
            messages.error(request, "Your booking session has expired or is invalid. Please start again.")
            print("DEBUG (Step1 GET): No temp_sales_booking_uuid found in session.")
            return redirect(reverse('inventory:all')) # Redirect to motorcycle list or home

        # 2. Fetch TempSalesBooking instance using session_uuid, not pk.
        try:
            temp_booking = get_object_or_404(TempSalesBooking, session_uuid=temp_booking_uuid)
            print(f"DEBUG (Step1 GET): Successfully fetched TempSalesBooking PK: {temp_booking.pk}, UUID: {temp_booking.session_uuid}")
        except Exception as e:
            messages.error(request, f"Your booking session could not be found or is invalid. Error: {e}")
            print(f"ERROR (Step1 GET): Failed to fetch TempSalesBooking with UUID {temp_booking_uuid}. Error: {e}")
            return redirect(reverse('inventory:all'))


        # 3. Fetch InventorySettings (singleton)
        inventory_settings = InventorySettings.objects.first()
        if not inventory_settings:
            messages.error(request, "Inventory settings are not configured. Please contact support.")
            print("DEBUG (Step1 GET): InventorySettings not found.")
            return redirect(reverse('inventory:all'))

        # 4. Initialize SalesProfileForm
        sales_profile_instance = None
        # Prioritize sales_profile linked to temp_booking
        if temp_booking.sales_profile:
            sales_profile_instance = temp_booking.sales_profile
        # Fallback to logged-in user's profile if no profile on temp_booking
        elif request.user.is_authenticated and hasattr(request.user, 'sales_profile'):
            sales_profile_instance = request.user.sales_profile
        
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
        # 1. Retrieve temp_sales_booking_uuid from session.
        temp_booking_uuid = request.session.get('temp_sales_booking_uuid')
        print(f"DEBUG (Step1 POST): Retrieved 'temp_sales_booking_uuid': {temp_booking_uuid}")

        if not temp_booking_uuid:
            messages.error(request, "Your booking session has expired or is invalid. Please start again.")
            print("DEBUG (Step1 POST): No temp_sales_booking_uuid found in session.")
            return redirect(reverse('inventory:all'))

        # 2. Fetch TempSalesBooking instance using session_uuid.
        try:
            temp_booking = get_object_or_404(TempSalesBooking, session_uuid=temp_booking_uuid)
            print(f"DEBUG (Step1 POST): Successfully fetched TempSalesBooking PK: {temp_booking.pk}, UUID: {temp_booking.session_uuid}")
        except Exception as e:
            messages.error(request, f"Your booking session could not be found or is invalid. Error: {e}")
            print(f"ERROR (Step1 POST): Failed to fetch TempSalesBooking with UUID {temp_booking_uuid}. Error: {e}")
            return redirect(reverse('inventory:all'))

        # 3. Fetch InventorySettings
        inventory_settings = InventorySettings.objects.first()
        if not inventory_settings:
            messages.error(request, "Inventory settings are not configured. Please contact support.")
            print("DEBUG (Step1 POST): InventorySettings not found.")
            return redirect(reverse('inventory:all'))

        # 4. Initialize SalesProfileForm with POST data
        sales_profile_instance = None
        # Prioritize sales_profile linked to temp_booking
        if temp_booking.sales_profile:
            sales_profile_instance = temp_booking.sales_profile
        # Fallback to logged-in user's profile if no profile on temp_booking
        elif request.user.is_authenticated and hasattr(request.user, 'sales_profile'):
            sales_profile_instance = request.user.sales_profile

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
                print(f"DEBUG (Step1 POST): SalesProfile saved and linked to TempSalesBooking UUID: {temp_booking.session_uuid}")

                messages.success(request, "Personal details saved. Proceed to booking details and appointment.")
                # Redirect to the next step: Booking Details and Appointment
                return redirect(reverse('inventory:step2_booking_details_and_appointment'))
        else:
            # Form is invalid, re-render the template with errors
            print(f"DEBUG (Step1 POST): SalesProfileForm is invalid. Errors: {sales_profile_form.errors}")
            context = {
                'sales_profile_form': sales_profile_form,
                'temp_booking': temp_booking,
                'inventory_settings': inventory_settings,
            }
            messages.error(request, "Please correct the errors below.")
            return render(request, self.template_name, context)
