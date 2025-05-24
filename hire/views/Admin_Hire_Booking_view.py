# hire/views/Admin_Hire_Booking_view.py

import datetime
from decimal import Decimal

from django.shortcuts import render, redirect
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
from .utils import calculate_hire_price, calculate_hire_duration_days


class AdminHireBookingView(View):
    """
    A single-page admin view for creating HireBooking records directly.
    It combines all steps into one form and allows for overrides.
    """
    template_name = 'hire/admin_hire_booking.html' 

    def _get_context_data(self, request, form):
        """
        Helper function to prepare the common context data for the template.
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
                {'id': m.id, 'daily_hire_rate': str(m.daily_hire_rate)} # Convert Decimal to string for JSON safety
                for m in all_motorcycles
            ],
            'packages_data': [
                {'id': p.id, 'package_price': str(p.package_price)}
                for p in all_packages
            ],
            'addons_data': [
                {'id': a.id, 'cost': str(a.cost), 'min_quantity': a.min_quantity, 'max_quantity': a.max_quantity}
                for a in all_addons
            ],
            'driver_profiles_data': [
                {'id': dp.id, 'name': dp.name, 'email': dp.email} # Example data, adjust as needed
                for dp in all_driver_profiles
            ]

        }
        return context


    def get(self, request, *args, **kwargs):
        """
        Handles GET requests to display the blank admin booking form.
        """
        form = AdminHireBookingForm()
        context = self._get_context_data(request, form)
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests to process the submitted admin booking form
        and create a HireBooking instance.
        """
        form = AdminHireBookingForm(request.POST)
        hire_settings = HireSettings.objects.first()

        if form.is_valid():
            # --- Section 1: Date & Time Selection ---
            pickup_date = form.cleaned_data['pick_up_date']
            pickup_time = form.cleaned_data['pick_up_time']
            return_date = form.cleaned_data['return_date']
            return_time = form.cleaned_data['return_time']

            # Calculate duration in days for price calculation
            duration_days = calculate_hire_duration_days(
                pickup_date, return_date, pickup_time, return_time
            )

            # --- Section 2: Motorcycle Selection & Rates ---
            motorcycle = form.cleaned_data['motorcycle']
            booked_daily_rate = form.cleaned_data['booked_daily_rate']

            # --- Section 3: Add-ons & Packages ---
            selected_package = form.cleaned_data.get('selected_package_instance')
            selected_addons_data = form.cleaned_data.get('selected_addons_data', [])

            total_package_price = Decimal('0.00')
            if selected_package:
                total_package_price = selected_package.package_price

            # --- Section 4: Driver Profile ---
            driver_profile = form.cleaned_data['driver_profile']

            # Determine if it's an international booking based on driver profile
            is_international_booking = not driver_profile.is_australian_resident

            # --- Section 5: Financial Details & Status ---
            currency = form.cleaned_data['currency']
            total_price_admin_entered = form.cleaned_data['total_price'] # This is the manually entered total
            payment_method = form.cleaned_data['payment_method']
            payment_status = form.cleaned_data['payment_status']
            status = form.cleaned_data['status']

            # Set amount_paid based on payment_status and total_price_admin_entered
            amount_paid = Decimal('0.00')
            if payment_status == 'paid':
                amount_paid = total_price_admin_entered
            elif payment_status == 'deposit_paid' and hire_settings and hire_settings.deposit_percentage is not None:
                deposit_percentage = Decimal(str(hire_settings.deposit_percentage)) / Decimal('100')
                amount_paid = total_price_admin_entered * deposit_percentage
                amount_paid = amount_paid.quantize(Decimal('0.01')) # Round to 2 decimal places

            # --- Section 6: Internal Notes ---
            internal_notes = form.cleaned_data.get('internal_notes')

            try:
                # Create the HireBooking instance directly
                hire_booking = HireBooking.objects.create(
                    motorcycle=motorcycle,
                    driver_profile=driver_profile,
                    pickup_date=pickup_date,
                    pickup_time=pickup_time,
                    return_date=return_date,
                    return_time=return_time,
                    booked_daily_rate=booked_daily_rate,
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

                # Add add-ons through the intermediate model (BookingAddOn)
                for item in selected_addons_data:
                    # Add-on cost is per item per day, so multiply by duration_days
                    BookingAddOn.objects.create(
                        hire_booking=hire_booking,
                        addon=item['addon'],
                        quantity=item['quantity'],
                        booked_addon_price=item['addon'].cost 
                    )

                messages.success(request, f"Hire Booking {hire_booking.booking_reference} created successfully!")
                return redirect('hire:admin_dashboard') 

            except Exception as e:
                messages.error(request, f"An error occurred while creating the booking: {e}")
                context = self._get_context_data(request, form) 
                return render(request, self.template_name, context)

        else:
            # Form is not valid, re-render with errors
            context = self._get_context_data(request, form)
            messages.error(request, "Please correct the errors below.")
            return render(request, self.template_name, context)