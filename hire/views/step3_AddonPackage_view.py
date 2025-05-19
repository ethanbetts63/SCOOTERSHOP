# hire/views/step3_AddonPackage_view.py

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.utils import timezone
import datetime # Import datetime for calculations

from inventory.models import Motorcycle
from ..models import AddOn, Package, TempHireBooking, HireBooking
# from ..forms.step3_AddonPackage_form import Step3AddonPackageForm # Assuming you'll create this
from ..views.utils import calculate_hire_price, calculate_hire_duration_days # Your utility functions
from dashboard.models import HireSettings # Assuming HireSettings is needed for pricing

class AddonPackageView(View):
    template_name = 'hire/step3_addons_and_packages.html'
    # form_class = Step3AddonPackageForm # Define or import your form

    def get(self, request, motorcycle_id=None, *args, **kwargs):
        # --- 1. Retrieve or Validate Temporary Booking ---
        temp_booking = self._get_temp_booking(request)
        if not temp_booking:
            return redirect('hire:step1_select_datetime') # Redirect if no temp booking

        hire_settings = HireSettings.objects.first() # Get settings

        # --- 2. Handle Motorcycle Selection (if ID is provided in URL) ---
        if motorcycle_id is not None:
            # This means the user clicked "Select" from Step 2
            try:
                selected_motorcycle = get_object_or_404(Motorcycle, pk=motorcycle_id)

                # Validate if the selected motorcycle is actually available for the dates
                # (This is a crucial re-check in case availability changed between step 2 load and click)
                if not self._is_motorcycle_available(selected_motorcycle, temp_booking):
                     messages.error(request, "The selected motorcycle is no longer available for your chosen dates. Please select another.")
                     return redirect('hire:step2_choose_bike') # Send back to bike selection

                # Link the selected motorcycle to the temporary booking
                temp_booking.motorcycle = selected_motorcycle

                # Calculate and store the base hire price for this motorcycle and period
                temp_booking.total_hire_price = calculate_hire_price(
                     selected_motorcycle,
                     timezone.make_aware(datetime.datetime.combine(temp_booking.pickup_date, temp_booking.pickup_time)),
                     timezone.make_aware(datetime.datetime.combine(temp_booking.return_date, temp_booking.return_time)),
                     hire_settings
                )
                # Store booked rates if needed for history/record (optional, can calculate from total_hire_price later)
                # temp_booking.booked_daily_rate = ...
                temp_booking.save() # Save the temporary booking with the selected bike and base price
                messages.success(request, f"'{selected_motorcycle.brand} {selected_motorcycle.model}' selected.")

            except Exception as e:
                # Handle cases like invalid motorcycle ID
                messages.error(request, "Error selecting motorcycle. Please try again.")
                print(f"Error selecting motorcycle in Step 3: {e}") # Log the error
                return redirect('hire:step2_choose_bike') # Send back to bike selection

        # --- 3. Ensure a Motorcycle is Selected before proceeding ---
        # If motorcycle_id was NOT provided, check if a motorcycle is already linked
        elif not temp_booking.motorcycle:
            messages.warning(request, "Please select a motorcycle first.")
            return redirect('hire:step2_choose_bike') # Send back if no bike is linked

        # --- 4. Load Available Add-ons and Packages ---
        available_addons = AddOn.objects.filter(is_available=True)
        available_packages = Package.objects.filter(is_available=True)

        # --- 5. Load currently selected Add-ons/Packages for this Temp Booking ---
        # You'll need to retrieve related TempBookingAddOn instances
        selected_addons_data = temp_booking.temp_booking_addons.all()
        selected_package = temp_booking.package # This is already on the temp booking

        # --- 6. Prepare Context ---
        context = {
            'temp_booking': temp_booking, # Pass the temp booking object
            'available_addons': available_addons,
            'available_packages': available_packages,
            'selected_addons_data': selected_addons_data, # Data for pre-selecting checkboxes/quantities
            'selected_package': selected_package, # For pre-selecting package radio button
            # 'form': self.form_class(), # Initialize form for add-on/package selection
        }

        return render(request, self.template_name, context)

    # No POST method here yet. The POST for Add-ons/Packages selection
    # will be handled by a separate method or URL, likely submitting to itself.
    # Example POST structure (will need a form for quantities/package selection):
    # def post(self, request, *args, **kwargs):
    #     temp_booking = self._get_temp_booking(request)
    #     if not temp_booking:
    #         return redirect('hire:step1_select_datetime')
    #
    #     form = self.form_class(request.POST) # Assuming a form handles selection
    #
    #     if form.is_valid():
    #          # Process selected addons and package from the form
    #          # Update temp_booking.package
    #          # Create/Update TempBookingAddOn instances related to temp_booking
    #          # Calculate temp_booking.total_addons_price and temp_booking.total_package_price
    #          # Recalculate temp_booking.grand_total
    #          # temp_booking.save()
    #          messages.success(request, "Add-ons and packages updated.")
    #          return redirect('hire:step4_has_account') # Redirect to the next step
    #     else:
    #         messages.error(request, "Please correct the errors below.")
    #         # Re-render the GET template with form errors and available/selected options
    #         available_addons = AddOn.objects.filter(is_available=True)
    #         available_packages = Package.objects.filter(is_available=True)
    #         context = {
    #             'temp_booking': temp_booking,
    #             'available_addons': available_addons,
    #             'available_packages': available_packages,
    #             'form': form, # Pass form with errors
    #             # You might need to re-populate selected_addons_data/selected_package from the temp_booking
    #             # or the form data if the form is complex.
    #         }
    #         return render(request, self.template_name, context)


    def _get_temp_booking(self, request):
        """Helper to retrieve the temporary booking from session."""
        temp_booking_id = request.session.get('temp_booking_id')
        temp_booking_uuid = request.session.get('temp_booking_uuid')
        if not temp_booking_id or not temp_booking_uuid:
            messages.warning(request, "Your booking session has expired or was not found. Please start again.")
            return None
        try:
            temp_booking = TempHireBooking.objects.get(id=temp_booking_id, session_uuid=temp_booking_uuid)
            # Basic check if the dates are still valid (optional, can be more thorough)
            if not temp_booking.pickup_date or not temp_booking.return_date or temp_booking.return_date < temp_booking.pickup_date:
                 messages.warning(request, "Booking dates are missing or invalid. Please select your dates again.")
                 return None # Forces user back to step 1
            return temp_booking
        except TempHireBooking.DoesNotExist:
            messages.error(request, "Your temporary booking could not be found. Please start again.")
            # Clear potentially stale session keys
            if 'temp_booking_id' in request.session:
                del request.session['temp_booking_id']
            if 'temp_booking_uuid' in request.session:
                del request.session['temp_booking_uuid']
            return None

    def _is_motorcycle_available(self, motorcycle, temp_booking):
        """Helper to re-check if a specific motorcycle is available for the temp booking dates."""
        if not temp_booking.pickup_date or not temp_booking.return_date or not temp_booking.pickup_time or not temp_booking.return_time:
            # Cannot check availability without dates
            return False

        pickup_datetime = timezone.make_aware(datetime.datetime.combine(temp_booking.pickup_date, temp_booking.pickup_time))
        return_datetime = timezone.make_aware(datetime.datetime.combine(temp_booking.return_date, temp_booking.return_time))

        # Check for conflicting confirmed bookings for this specific motorcycle
        conflicting_bookings = HireBooking.objects.filter(
    # Combine the Q objects for date and time range check
        (Q(pickup_date__lt=return_datetime.date()) |
        (Q(pickup_date=return_datetime.date()) & Q(pickup_time__lte=return_datetime.time()))) &
        (Q(return_date__gt=pickup_datetime.date()) |
        (Q(return_date=pickup_datetime.date()) & Q(return_time__gte=pickup_datetime.time()))),
        # Place keyword arguments after positional arguments (the combined Q object)
        motorcycle=motorcycle,
        status__in=['pending', 'confirmed', 'in_progress'] # Check against active bookings
        ).exists() # Check if *any* such booking exists # Check if *any* such booking exists

        # Also check against other *temporary* bookings for this motorcycle,
        # excluding the current temporary booking itself. This prevents two users
        # from temporarily selecting the same bike at the same time.
        # However, this adds complexity and might not be strictly necessary
        # if the race condition is handled at final confirmation. For now,
        # let's just check against confirmed bookings. You can add this if needed.
        # conflicting_temp_bookings = TempHireBooking.objects.filter(
        #      motorcycle=motorcycle,
        #      # ... date/time conflict check ...
        # ).exclude(id=temp_booking.id).exists()


        # Check license compatibility again
        if not temp_booking.has_motorcycle_license and motorcycle.engine_size > 50:
             return False

        return not conflicting_bookings # Motorcycle is available if no conflicts


# NOTE: You will need to create hire/forms/step3_AddonPackage_form.py
# and the corresponding template hire/templates/hire/step3_addons_and_packages.html
# to display and select add-ons/packages. The POST method for this view
# will process that form and update the TempHireBooking instance.