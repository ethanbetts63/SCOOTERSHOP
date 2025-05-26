# hire/views/step3_AddonPackage_view.py

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.utils import timezone
import datetime
from decimal import Decimal
from django.http import HttpResponseRedirect # Import HttpResponseRedirect

from inventory.models import Motorcycle
from ..models import AddOn, Package, TempHireBooking, HireBooking, TempBookingAddOn
from ..forms.step3_AddonPackage_form import Step3AddOnsPackagesForm
from ..views.utils import calculate_hire_price, calculate_hire_duration_days, is_motorcycle_available # Import the utility function
from dashboard.models import HireSettings

class AddonPackageView(View):
    template_name = 'hire/step3_addons_and_packages.html'

    def get(self, request, motorcycle_id=None, *args, **kwargs):
        temp_booking = self._get_temp_booking(request)
        if not temp_booking:
            return redirect('hire:step2_choose_bike')

        hire_settings = HireSettings.objects.first()

        if motorcycle_id is not None:
            try:
                motorcycle = get_object_or_404(Motorcycle, id=motorcycle_id)
            except Exception:
                messages.error(request, "Selected motorcycle not found.")
                return redirect('hire:step2_choose_bike')

            # Call the utility function to check motorcycle availability.
            # This function now handles messages and redirects internally.
            availability_result = is_motorcycle_available(request, motorcycle, temp_booking)
            
            # If the utility function returned a redirect, we should return that redirect.
            # Otherwise, if it returned False, it means a message was added, and we should redirect.
            if isinstance(availability_result, HttpResponseRedirect): # Correctly check for HttpResponseRedirect
                return availability_result
            elif not availability_result: # If it returned False (and added a message)
                return redirect('hire:step2_choose_bike')

            # License check: This remains in the view as it's specific to this step's logic
            if not temp_booking.has_motorcycle_license and int(motorcycle.engine_size) > 50:
                 messages.error(request, "You require a full motorcycle license for this motorcycle.")
                 return redirect('hire:step2_choose_bike')

            temp_booking.motorcycle = motorcycle
            hire_duration_days = calculate_hire_duration_days(
                temp_booking.pickup_date, temp_booking.return_date, temp_booking.pickup_time, temp_booking.return_time
            )
            temp_booking.total_hire_price = calculate_hire_price(
                motorcycle,
                hire_duration_days,
                hire_settings
            )
            temp_booking.save()
            messages.success(request, f"Motorcycle {motorcycle.model} selected successfully. Now choose add-ons and packages.")

        available_packages = Package.objects.none() # Initialize as empty QuerySet
        if hire_settings and hire_settings.packages_enabled:
            all_available_packages = Package.objects.filter(is_available=True)

            if not all_available_packages.exists():
                basic_package, created = Package.objects.get_or_create(
                    name="Basic Hire",
                    defaults={
                        'description': "Standard hire package with no additional items.",
                        'package_price': Decimal('0.00'),
                        'is_available': True
                    }
                )
                if created or not basic_package.is_available:
                    basic_package.is_available = True
                    basic_package.save()
                available_packages = Package.objects.filter(id=basic_package.id) # Ensure it's a QuerySet
                if not temp_booking.package:
                    temp_booking.package = basic_package
                    temp_booking.total_package_price = basic_package.package_price
                    temp_booking.save()
                    messages.info(request, "No custom packages found, a default 'Basic Hire' package has been selected.")
            else:
                available_packages = all_available_packages # Keep it as a QuerySet

                if not temp_booking.package:
                    basic_package_option = all_available_packages.filter(name="Basic Hire").first()
                    if basic_package_option:
                        temp_booking.package = basic_package_option
                        temp_booking.total_package_price = basic_package_option.package_price
                        temp_booking.save()
                    elif all_available_packages.exists():
                        temp_booking.package = all_available_packages.first()
                        temp_booking.total_package_price = all_available_packages.first().package_price
                        temp_booking.save()
        else:
            if temp_booking.package:
                temp_booking.package = None
                temp_booking.total_package_price = 0
                temp_booking.save()

        # Get all add-ons (including unavailable ones) to pass to the form for comprehensive validation
        # The form's __init__ will handle filtering for display
        all_addons_for_form = AddOn.objects.all()

        initial_data = {}
        if temp_booking.package:
            initial_data['package'] = temp_booking.package.id
        # Populate initial data only for add-ons that will be displayed
        # The form's __init__ will handle filtering based on the selected package
        for temp_addon in temp_booking.temp_booking_addons.all():
            # Check if this temp_addon's original addon is still active and relevant
            # The form's __init__ will decide if it should be displayed
            if all_addons_for_form.filter(id=temp_addon.addon.id).exists(): # Check against all_addons_for_form
                initial_data[f'addon_{temp_addon.addon.id}_selected'] = True
                initial_data[f'addon_{temp_addon.addon.id}_quantity'] = temp_addon.quantity

        form = Step3AddOnsPackagesForm(
            initial=initial_data,
            available_packages=available_packages,
            available_addons=all_addons_for_form, # Pass ALL add-ons to the form
            selected_package_instance=temp_booking.package # Pass the selected package instance
        )
        print(f"DEBUG (View GET): Form's display_addons contains: {[a['addon'].name for a in form.display_addons]}")

        context = {
            'temp_booking': temp_booking,
            'form': form,
            'available_packages': available_packages,
            'all_active_addons': AddOn.objects.filter(is_available=True), # For JS mapping of only active addons
            'hire_settings': hire_settings,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        temp_booking = self._get_temp_booking(request)
        if not temp_booking:
            messages.error(request, "Session expired. Please start again.")
            return redirect('hire:step2_choose_bike')

        hire_settings = HireSettings.objects.first()
        available_packages = Package.objects.filter(is_available=True)
        # Get all add-ons (including unavailable ones) to pass to the form for comprehensive validation
        all_addons_for_form = AddOn.objects.all()

        # Get the selected package from POST data to pass to the form's __init__
        # This is crucial for the form to correctly filter/adjust add-ons during POST validation
        selected_package_id = request.POST.get('package')
        selected_package_instance_for_form = None
        if selected_package_id:
            try:
                selected_package_instance_for_form = Package.objects.get(id=selected_package_id)
            except Package.DoesNotExist:
                pass # Handle case where package might not exist (e.g., tampered data)

        form = Step3AddOnsPackagesForm(
            request.POST,
            available_packages=available_packages,
            available_addons=all_addons_for_form, # Pass ALL add-ons to the form
            selected_package_instance=selected_package_instance_for_form # Pass for POST validation
        )

        if form.is_valid():
            selected_package = form.cleaned_data.get('selected_package')
            selected_addons_data = form.cleaned_data.get('selected_addons', [])
            print(f"DEBUG (View POST - form valid): selected_addons_data: {[{'addon': item['addon'].name, 'quantity': item['quantity']} for item in selected_addons_data]}")


            temp_booking.package = selected_package
            temp_booking.total_package_price = selected_package.package_price if selected_package else Decimal('0.00')

            # Clear existing TempBookingAddOn entries
            temp_booking.temp_booking_addons.all().delete()

            total_addons_price = Decimal('0.00')
            hire_duration_days = calculate_hire_duration_days(
                temp_booking.pickup_date, temp_booking.return_date, temp_booking.pickup_time, temp_booking.return_time
            )
            print(f"DEBUG (View POST - form valid): hire_duration_days: {hire_duration_days}")


            # Create TempBookingAddOn entries for the *additional* selected add-ons
            for item in selected_addons_data:
                addon = item['addon']
                quantity = item['quantity']
                
                # No need to check if addon is in selected_package.add_ons.all() here,
                # as the form's filtering ensures these are "additional" add-ons.
                TempBookingAddOn.objects.create(
                    temp_booking=temp_booking,
                    addon=addon,
                    quantity=quantity,
                    booked_addon_price=addon.cost
                )
                cost_for_this_addon = addon.cost * quantity * hire_duration_days
                total_addons_price += cost_for_this_addon
                print(f"DEBUG (View POST - form valid): Added {addon.name} (qty={quantity}) cost: {cost_for_this_addon}. Current total_addons_price: {total_addons_price}")


            # Also, add the price of add-ons *included* in the package if max_quantity = 1
            # These are not part of selected_addons_data, but their cost is part of the package price.
            # We need to ensure their cost is reflected in total_addons_price if they are part of the package
            # and they have max_quantity = 1.
            # This logic might need to be refined based on how package pricing is handled.
            # If package_price already includes the cost of these addons, then no need to add here.
            # For max_quantity > 1 addons, their 'base' quantity (1) is included in package price,
            # and any *additional* quantity is added via selected_addons_data.

            temp_booking.total_addons_price = total_addons_price # This now only reflects additional add-ons
            temp_booking.grand_total = temp_booking.total_hire_price + temp_booking.total_package_price + temp_booking.total_addons_price
            temp_booking.save()
            print(f"DEBUG (View POST - form valid): Final total_addons_price: {temp_booking.total_addons_price}")
            print(f"DEBUG (View POST - form valid): Final grand_total: {temp_booking.grand_total}")


            messages.success(request, "Add-ons and packages updated successfully.")
            if request.user.is_authenticated:
                return redirect('hire:step4_has_account')
            else:
                return redirect('hire:step4_no_account')
        else:
            print(f"DEBUG (View POST - form invalid): Form errors: {form.errors}")
            messages.error(request, "Please correct the errors below.")
            context = {
                'temp_booking': temp_booking,
                'form': form,
                'available_packages': available_packages,
                'all_active_addons': AddOn.objects.filter(is_available=True), # For JS mapping of only active addons
                'hire_settings': hire_settings,
            }
            return render(request, self.template_name, context)

    def _get_temp_booking(self, request):
        session_uuid = request.session.get('temp_booking_uuid')
        if not session_uuid:
            return None
        try:
            return TempHireBooking.objects.get(session_uuid=session_uuid)
        except TempHireBooking.DoesNotExist:
            return None