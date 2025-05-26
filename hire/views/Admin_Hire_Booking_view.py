# hire/views/Admin_Hire_Booking_view.py

import datetime
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.utils import timezone
from django.urls import reverse # Import reverse for dynamic URL lookup

# Import models
from inventory.models import Motorcycle
from ..models import AddOn, Package, DriverProfile, HireBooking, BookingAddOn
from dashboard.models import HireSettings, BlockedHireDate

# Import the AdminHireBookingForm
from ..forms.Admin_Hire_Booking_form import AdminHireBookingForm

# Import utility functions
from .utils import get_overlapping_motorcycle_bookings
from .hire_pricing import calculate_motorcycle_hire_price

class AdminHireBookingView(View):
    """
    A single-page admin view for creating and editing HireBooking records directly.
    It combines all steps into one form and allows for overrides.
    """
    template_name = 'hire/admin_hire_booking.html'

    def _get_context_data(self, request, form, booking_instance=None):
        """
        Helper function to prepare the common context data for the template.
        Accepts an optional booking_instance for edit mode.
        """
        hire_settings = HireSettings.objects.first()

        # Fetch all necessary instances for dynamic updates in JS
        all_motorcycles = Motorcycle.objects.filter(is_available=True, conditions__name='hire').distinct()
        all_packages = Package.objects.filter(is_available=True)
        all_addons = AddOn.objects.filter(is_available=True)
        all_driver_profiles = DriverProfile.objects.all().order_by('name')

        context = {
            'form': form,
            'hire_settings': hire_settings,
            'motorcycles_data': [
                {'id': m.id, 'daily_hire_rate': str(m.daily_hire_rate) if m.daily_hire_rate is not None else None, 'hourly_hire_rate': str(m.hourly_hire_rate) if m.hourly_hire_rate is not None else None}
                for m in all_motorcycles
            ],
            'packages_data': [
                {'id': p.id, 'name': p.name, 'package_price': str(p.package_price)}
                for p in all_packages
            ],
            'addons_data': [
                {'id': a.id, 'cost': str(a.cost), 'min_quantity': a.min_quantity, 'max_quantity': a.max_quantity}
                for a in all_addons
            ],
            'driver_profiles_data': [
                {'id': dp.id, 'name': dp.name, 'email': dp.email}
                for dp in all_driver_profiles
            ],
            'default_daily_rate': str(hire_settings.default_daily_rate) if hire_settings and hire_settings.default_daily_rate is not None else "0.00",
            'default_hourly_rate': str(hire_settings.default_hourly_rate) if hire_settings and hire_settings.default_hourly_rate is not None else "0.00",
            'booking': booking_instance, # Pass the booking instance to the template
        }
        return context


    def get(self, request, pk=None, *args, **kwargs):
        """
        Handles GET requests to display the admin booking form.
        If pk is provided, it fetches and pre-populates an existing booking.
        """
        booking_instance = None
        if pk:
            try:
                booking_instance = get_object_or_404(HireBooking, pk=pk)
                form = AdminHireBookingForm(instance=booking_instance)
                messages.info(request, f"Editing Hire Booking: {booking_instance.booking_reference}")
            except Exception as e:
                messages.error(request, f"Error loading booking for edit: {e}")
                return redirect('dashboard:hire_bookings') # Redirect to hire bookings list if not found
        else:
            form = AdminHireBookingForm()
            messages.info(request, "Creating New Hire Booking")

        # Clear any previous overlap warning from session on initial GET
        if 'last_overlap_attempt' in request.session:
            del request.session['last_overlap_attempt']
            print("DEBUG: Cleared 'last_overlap_attempt' from session on GET request.")

        context = self._get_context_data(request, form, booking_instance)
        return render(request, self.template_name, context)

    def post(self, request, pk=None, *args, **kwargs):
        """
        Handles POST requests to process the submitted admin booking form
        and create/update a HireBooking instance, with overlap override logic.
        """
        booking_instance = None
        if pk:
            try:
                booking_instance = get_object_or_404(HireBooking, pk=pk)
                form = AdminHireBookingForm(request.POST, instance=booking_instance)
            except Exception as e:
                messages.error(request, f"Error loading booking for update: {e}")
                return redirect('dashboard:hire_bookings') # Redirect to hire bookings list if not found
        else:
            form = AdminHireBookingForm(request.POST)

        hire_settings = HireSettings.objects.first()

        print("\n--- DEBUGGING POST REQUEST ---")
        print(f"Form is valid: {form.is_valid()}")

        if form.is_valid():
            # --- Extract cleaned data ---
            pickup_date = form.cleaned_data['pick_up_date']
            pickup_time = form.cleaned_data['pick_up_time']
            return_date = form.cleaned_data['return_date']
            return_time = form.cleaned_data['return_time']
            motorcycle = form.cleaned_data['motorcycle']

            # Combine date and time for the overlap identifier
            pickup_datetime_for_identifier = timezone.make_aware(datetime.datetime.combine(pickup_date, pickup_time))
            return_datetime_for_identifier = timezone.make_aware(datetime.datetime.combine(return_date, return_time))

            # --- Motorcycle Overlap Check using utility function ---
            # Create a unique identifier for the current potential overlap
            current_overlap_identifier = (
                motorcycle.id,
                pickup_datetime_for_identifier.isoformat(),
                return_datetime_for_identifier.isoformat()
            )
            print(f"DEBUG: Current overlap identifier: {current_overlap_identifier}")

            last_overlap_attempt_raw = request.session.get('last_overlap_attempt')
            last_overlap_attempt = tuple(last_overlap_attempt_raw) if isinstance(last_overlap_attempt_raw, list) else last_overlap_attempt_raw
            print(f"DEBUG: 'last_overlap_attempt' from session (after conversion): {last_overlap_attempt}")

            # Call the utility function to get overlapping bookings
            # Exclude the current booking instance from overlap check if editing
            exclude_booking_id = booking_instance.id if booking_instance else None
            actual_overlaps = get_overlapping_motorcycle_bookings(
                motorcycle,
                pickup_date,
                pickup_time,
                return_date,
                return_time,
                exclude_booking_id=exclude_booking_id # Pass the ID to exclude
            )
            print(f"DEBUG: Actual overlaps found: {actual_overlaps}")


            # --- Override Logic ---
            allow_booking_creation_or_update = True
            if actual_overlaps:
                print(f"DEBUG: Overlaps detected. Number of overlaps: {len(actual_overlaps)}")
                if last_overlap_attempt == current_overlap_identifier:
                    # This is a re-submission with the same overlapping dates/motorcycle, allow override
                    messages.info(request, "Overlap warning overridden. Proceeding despite overlap.")
                    if 'last_overlap_attempt' in request.session:
                        del request.session['last_overlap_attempt'] # Clear session after override
                        print("DEBUG: 'last_overlap_attempt' cleared from session (override successful).")
                else:
                    # First time this overlap is detected, issue warning
                    overlap_messages = [
                        f"Booking {b.booking_reference} ({b.pickup_date.strftime('%Y-%m-%d')} {b.pickup_time.strftime('%H:%M')} to {b.return_date.strftime('%Y-%m-%d')} {b.return_time.strftime('%H:%M')})"
                        for b in actual_overlaps
                    ]
                    messages.warning(
                        request,
                        f"These dates for this motorcycle overlap with existing booking(s): "
                        f"{'; '.join(overlap_messages)}. "
                        f"To override this warning and proceed, submit again with unchanged dates."
                    )
                    request.session['last_overlap_attempt'] = current_overlap_identifier
                    print(f"DEBUG: 'last_overlap_attempt' set in session for warning: {current_overlap_identifier}")
                    allow_booking_creation_or_update = False
            else:
                # No overlaps detected, or previous overlap was resolved
                print("DEBUG: No overlaps detected.")
                if 'last_overlap_attempt' in request.session:
                    del request.session['last_overlap_attempt'] # Clear if no overlap
                    print("DEBUG: 'last_overlap_attempt' cleared from session (no overlap).")

            print(f"DEBUG: allow_booking_creation_or_update after overlap logic: {allow_booking_creation_or_update}")

            if not allow_booking_creation_or_update:
                print("DEBUG: Booking creation/update NOT allowed. Re-rendering form with errors/warnings.")
                context = self._get_context_data(request, form, booking_instance)
                return render(request, self.template_name, context)

            # --- If we reach here, either no overlap or override is allowed ---
            print("DEBUG: Proceeding with booking creation/update.")

            # Calculate duration in days for price calculation (not directly saved, but useful for context)
            duration_days = calculate_hire_duration_days(
                pickup_date, return_date, pickup_time, return_time
            )

            # --- Prepare data for saving/updating ---
            booked_daily_rate = form.cleaned_data['booked_daily_rate']
            booked_hourly_rate = form.cleaned_data['booked_hourly_rate']
            selected_package = form.cleaned_data.get('selected_package_instance')
            selected_addons_data = form.cleaned_data.get('selected_addons_data', [])
            total_package_price = selected_package.package_price if selected_package else Decimal('0.00')
            driver_profile = form.cleaned_data['driver_profile']
            is_international_booking = not driver_profile.is_australian_resident
            currency = form.cleaned_data['currency']
            total_price_admin_entered = form.cleaned_data['total_price']
            payment_method = form.cleaned_data['payment_method']
            payment_status = form.cleaned_data['payment_status']
            status = form.cleaned_data['status']
            internal_notes = form.cleaned_data.get('internal_notes')

            amount_paid = Decimal('0.00')
            if payment_status == 'paid':
                amount_paid = total_price_admin_entered
            elif payment_status == 'deposit_paid' and hire_settings and hire_settings.deposit_percentage is not None:
                deposit_percentage = Decimal(str(hire_settings.deposit_percentage)) / Decimal('100')
                amount_paid = total_price_admin_entered * deposit_percentage
                amount_paid = amount_paid.quantize(Decimal('0.01'))

            try:
                if booking_instance:
                    # Update existing HireBooking instance
                    booking_instance.motorcycle = motorcycle
                    booking_instance.driver_profile = driver_profile
                    booking_instance.pickup_date = pickup_date
                    booking_instance.pickup_time = pickup_time
                    booking_instance.return_date = return_date
                    booking_instance.return_time = return_time
                    booking_instance.booked_daily_rate = booked_daily_rate
                    booking_instance.booked_hourly_rate = booked_hourly_rate
                    booking_instance.total_price = total_price_admin_entered
                    booking_instance.amount_paid = amount_paid
                    booking_instance.payment_status = payment_status
                    booking_instance.payment_method = payment_method
                    booking_instance.status = status
                    booking_instance.currency = currency
                    booking_instance.internal_notes = internal_notes
                    booking_instance.is_international_booking = is_international_booking
                    booking_instance.package = selected_package
                    booking_instance.total_package_price = total_package_price
                    booking_instance.save() # Save the updated instance

                    # Update add-ons: clear existing and add new ones
                    # CORRECTED: Use the related_name 'booking_addons'
                    booking_instance.booking_addons.all().delete() # Remove all existing add-ons
                    for item in selected_addons_data:
                        BookingAddOn.objects.create(
                            booking=booking_instance,
                            addon=item['addon'],
                            quantity=item['quantity'],
                            booked_addon_price=item['addon'].cost
                        )
                    messages.success(request, f"Hire Booking {booking_instance.booking_reference} updated successfully!")
                else:
                    # Create new HireBooking instance
                    hire_booking = HireBooking.objects.create(
                        motorcycle=motorcycle,
                        driver_profile=driver_profile,
                        pickup_date=pickup_date,
                        pickup_time=pickup_time,
                        return_date=return_date,
                        return_time=return_time,
                        booked_daily_rate=booked_daily_rate,
                        booked_hourly_rate=booked_hourly_rate,
                        total_price=total_price_admin_entered,
                        amount_paid=amount_paid,
                        payment_status=payment_status,
                        payment_method=payment_method,
                        status=status,
                        currency=currency,
                        internal_notes=internal_notes,
                        is_international_booking=is_international_booking,
                        package=selected_package,
                        booked_package_price=total_package_price
                    )
                    booking_instance = hire_booking # Set booking_instance for redirect

                    # Add add-ons through the intermediate model (BookingAddOn)
                    for item in selected_addons_data:
                        BookingAddOn.objects.create(
                            booking=hire_booking,
                            addon=item['addon'],
                            quantity=item['quantity'],
                            booked_addon_price=item['addon'].cost
                        )
                    messages.success(request, f"Hire Booking {hire_booking.booking_reference} created successfully!")

                # Redirect to the detail view of the created/updated booking
                return redirect('dashboard:hire_booking_details', pk=booking_instance.pk)

            except Exception as e:
                messages.error(request, f"An error occurred while saving the booking: {e}")
                context = self._get_context_data(request, form, booking_instance)
                return render(request, self.template_name, context)

        else:
            # Form is not valid, re-render with errors
            print("DEBUG: Form is NOT valid. Re-rendering form with errors.")
            context = self._get_context_data(request, form, booking_instance)
            messages.error(request, "Please correct the errors below.")
            return render(request, self.template_name, context)
