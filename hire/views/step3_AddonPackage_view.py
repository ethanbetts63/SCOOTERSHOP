# hire/views/step3_AddonPackage_view.py

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.utils import timezone
import datetime # Import datetime for calculations
from decimal import Decimal # Import Decimal for monetary values

from inventory.models import Motorcycle
from ..models import AddOn, Package, TempHireBooking, HireBooking
# from ..forms.step3_AddonPackage_form import Step3AddonPackageForm # Assuming you'll create this
from ..views.utils import calculate_hire_price, calculate_hire_duration_days # Your utility functions
from dashboard.models import HireSettings # Assuming HireSettings is in your dashboard app

class AddonPackageView(View):
    template_name = 'hire/step3_addons_and_packages.html'
    # form_class = Step3AddonPackageForm # Define or import your form

    def get(self, request, motorcycle_id=None, *args, **kwargs):
        # --- 1. Retrieve or Validate Temporary Booking ---
        temp_booking = self._get_temp_booking(request)
        if not temp_booking:
            return redirect('hire:step1_select_datetime') # Redirect if no temp booking

        hire_settings = HireSettings.objects.first() # Get settings instance

        # --- 2. Handle Motorcycle Selection (if ID is provided in URL) ---
        if motorcycle_id is not None:
            # This means the user clicked "Select" from Step 2
            try:
                motorcycle = get_object_or_404(Motorcycle, id=motorcycle_id)
            except Exception: # More specific exception handling is recommended
                messages.error(request, "Selected motorcycle not found.")
                return redirect('hire:step2_choose_bike')

            # Check if the motorcycle is available for the selected dates/times
            if not self._is_motorcycle_available(motorcycle, temp_booking):
                messages.error(request, "The selected motorcycle is not available for your chosen dates/times or license type.")
                return redirect('hire:step2_choose_bike')

            temp_booking.motorcycle = motorcycle
            # Recalculate motorcycle hire price based on the selected motorcycle and duration
            # Ensure calculate_hire_price uses the motorcycle's specific rates if set
            hire_duration_days = calculate_hire_duration_days(
                temp_booking.pickup_date, temp_booking.return_date
            )
            temp_booking.total_hire_price = calculate_hire_price(
                motorcycle, temp_booking.pickup_date, temp_booking.return_date, hire_settings # Pass motorcycle and settings
            )
            temp_booking.save()
            messages.success(request, f"Motorcycle {motorcycle.model} selected successfully. Now choose add-ons and packages.")


        # --- 3. Handle Package Selection Logic based on HireSettings ---
        available_packages = []
        if hire_settings and hire_settings.packages_enabled:
            # Fetch all available packages
            all_available_packages = Package.objects.filter(is_available=True)

            # If no packages exist, create a default "Basic Hire" package
            if not all_available_packages.exists():
                basic_package, created = Package.objects.get_or_create(
                    name="Basic Hire",
                    defaults={
                        'description': "Standard hire package with no additional items.",
                        'package_price': Decimal('0.00'),
                        'is_available': True
                    }
                )
                # Ensure it's available if it was just created or found as unavailable
                if created or not basic_package.is_available:
                    basic_package.is_available = True
                    basic_package.save()
                # Use this basic package as the only available option
                available_packages = [basic_package]
                # If there are no other packages, make this the default selection
                if not temp_booking.package:
                    temp_booking.package = basic_package
                    temp_booking.total_package_price = basic_package.package_price
                    temp_booking.save()
                    messages.info(request, "No custom packages found, a default 'Basic Hire' package has been selected.")
            else:
                # If packages exist, use them
                available_packages = list(all_available_packages) # Convert queryset to list

                # If no package is currently selected in temp_booking,
                # and there are packages available, try to select the first one or a "Basic Hire" if it exists
                if not temp_booking.package:
                    # Try to find a package named "Basic Hire" if it exists among the available ones
                    basic_package_option = next((p for p in available_packages if p.name == "Basic Hire"), None)
                    if basic_package_option:
                        temp_booking.package = basic_package_option
                        temp_booking.total_package_price = basic_package_option.package_price
                        temp_booking.save()
                    elif available_packages: # If no basic package but other packages exist, select the first
                        temp_booking.package = available_packages[0]
                        temp_booking.total_package_price = available_packages[0].package_price
                        temp_booking.save()


        else: # packages_enabled is False
            # If packages are disabled in settings, ensure no package is selected
            if temp_booking.package:
                temp_booking.package = None
                temp_booking.total_package_price = 0
                temp_booking.save()
            # No packages will be passed to the context.

        # --- 4. Prepare Add-ons ---
        available_addons = []
        if hire_settings and hire_settings.add_ons_enabled:
            available_addons = AddOn.objects.filter(is_available=True)

        # --- 5. Prepare Context for Template ---
        context = {
            'temp_booking': temp_booking,
            'available_packages': available_packages,
            'available_addons': available_addons,
            'hire_settings': hire_settings, # Pass settings to context for checks in template
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        # This is where you'll process the form submission
        # (after you define Step3AddonPackageForm)
        temp_booking = self._get_temp_booking(request)
        if not temp_booking:
            messages.error(request, "Session expired. Please start again.")
            return redirect('hire:step1_select_datetime')

        hire_settings = HireSettings.objects.first()

        # Assuming you will create Step3AddonPackageForm and use it here
        # form = self.form_class(request.POST, instance=temp_booking)
        # if form.is_valid():
            # Process package selection
            # selected_package_id = request.POST.get('package_id')
            # if hire_settings.packages_enabled and selected_package_id:
            #     selected_package = get_object_or_404(Package, id=selected_package_id, is_available=True)
            #     temp_booking.package = selected_package
            #     temp_booking.total_package_price = selected_package.package_price
            # else:
            #     temp_booking.package = None
            #     temp_booking.total_package_price = 0

            # Process add-on selections (quantities)
            # This would likely involve a formset or iterating through specific fields
            # and updating TempBookingAddOn instances related to temp_booking.
            # Example:
            # temp_booking.temp_booking_addons.all().delete() # Clear existing
            # for addon in AddOn.objects.filter(is_available=True):
            #     addon_checkbox_name = f'addon_id_{addon.id}'
            #     quantity_input_name = f'quantity_{addon.id}'
            #     if request.POST.get(addon_checkbox_name) == str(addon.id):
            #         quantity = int(request.POST.get(quantity_input_name, 1))
            #         # Check if this addon is part of the selected package, if so, don't add it individually
            #         # This logic should mirror the JS on the frontend
            #         # If it's not part of the package or no package is selected
            #         TempBookingAddOn.objects.create(
            #             temp_booking=temp_booking,
            #             addon=addon,
            #             quantity=quantity,
            #             booked_addon_price=addon.cost # Store current cost
            #         )


            # Recalculate grand_total based on selected package and add-ons
            # hire_duration_days = calculate_hire_duration_days(...)
            # temp_booking.total_addons_price = ... (sum of selected add-ons * duration)
            # temp_booking.grand_total = temp_booking.total_hire_price + temp_booking.total_addons_price + temp_booking.total_package_price
            # temp_booking.save()

        messages.success(request, "Add-ons and packages updated successfully.")
        return redirect('hire:step4_customer_details') # Redirect to next step
        # else:
            # messages.error(request, "Please correct the errors below.")
            # context = {
            #     'form': form,
            #     'temp_booking': temp_booking,
            #     'available_packages': Package.objects.filter(is_available=True),
            #     'available_addons': AddOn.objects.filter(is_available=True),
            #     'hire_settings': hire_settings,
            # }
            # return render(request, self.template_name, context)

        # Placeholder for now, you will replace with actual form processing
        messages.error(request, "Form processing not yet implemented for Step 3. Please complete form and submission logic.")
        return redirect('hire:step3_addons_and_packages') # Stay on this page for now

    def _get_temp_booking(self, request):
        """Helper to retrieve the current TempHireBooking from session."""
        session_uuid = request.session.get('temp_booking_uuid')
        if not session_uuid:
            return None
        try:
            return TempHireBooking.objects.get(session_uuid=session_uuid)
        except TempHireBooking.DoesNotExist:
            return None

    def _is_motorcycle_available(self, motorcycle, temp_booking):
        """Helper to check motorcycle availability for the given dates/times."""
        if not temp_booking.pickup_date or not temp_booking.pickup_time or \
           not temp_booking.return_date or not temp_booking.return_time:
            messages.error(self.request, "Please select valid pickup and return dates/times first.")
            return False

        # Combine date and time into datetimes for comparison
        pickup_datetime = timezone.make_aware(
            datetime.datetime.combine(temp_booking.pickup_date, temp_booking.pickup_time)
        )
        return_datetime = timezone.make_aware(
            datetime.datetime.combine(temp_booking.return_date, temp_booking.return_time)
        )

        # Ensure return is after pickup
        if return_datetime <= pickup_datetime:
            messages.error(self.request, "Return time must be after pickup time.")
            return False

        # Exclude the current temporary booking if it exists (for edits)
        # This part handles conflicts with *confirmed* HireBookings only.
        conflicting_bookings = HireBooking.objects.filter(
            motorcycle=motorcycle,
            # Check for overlapping time periods
            pickup_date__lt=temp_booking.return_date, # Booked pickup is before temp_booking return
            return_date__gt=temp_booking.pickup_date # Booked return is after temp_booking pickup
        ).exists()

        # Check license compatibility again
        if not temp_booking.has_motorcycle_license and int(motorcycle.engine_size) > 50:
             messages.error(self.request, "You require a full motorcycle license for this motorcycle.")
             return False

        return not conflicting_bookings # Motorcycle is available if no conflicts