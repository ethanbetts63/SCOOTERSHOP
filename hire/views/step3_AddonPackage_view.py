from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.utils import timezone
import datetime
from decimal import Decimal, ROUND_HALF_UP
from django.http import HttpResponseRedirect

from inventory.models import Motorcycle
from ..models import AddOn, Package, TempHireBooking, HireBooking, TempBookingAddOn
from ..forms.step3_AddonPackage_form import Step3AddOnsPackagesForm
from ..utils import is_motorcycle_available
from ..hire_pricing import (
    calculate_motorcycle_hire_price,
    calculate_package_price,
    calculate_addon_price,
    calculate_total_addons_price,
    calculate_booking_grand_total,
    _calculate_price_by_strategy
)
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

            availability_result = is_motorcycle_available(request, motorcycle, temp_booking)
            
            if isinstance(availability_result, HttpResponseRedirect):
                return availability_result
            elif not availability_result:
                return redirect('hire:step2_choose_bike')

            if not temp_booking.has_motorcycle_license and int(motorcycle.engine_size) > 50:
                messages.error(request, "You require a full motorcycle license for this motorcycle.")
                return redirect('hire:step2_choose_bike')

            temp_booking.motorcycle = motorcycle
            
            temp_booking.total_hire_price = calculate_motorcycle_hire_price(
                motorcycle,
                temp_booking.pickup_date,
                temp_booking.return_date,
                temp_booking.pickup_time,
                temp_booking.return_time,
                hire_settings
            )
            temp_booking.save()
            messages.success(request, f"Motorcycle {motorcycle.model} selected successfully. Now choose add-ons and packages.")

        available_packages = Package.objects.none()
        if hire_settings and hire_settings.packages_enabled:
            all_available_packages = Package.objects.filter(is_available=True)

            if not all_available_packages.exists():
                basic_package, created = Package.objects.get_or_create(
                    name="Basic Hire",
                    defaults={
                        'description': "Standard hire package with no additional items.",
                        'hourly_cost': Decimal('0.00'),
                        'daily_cost': Decimal('0.00'),
                        'is_available': True
                    }
                )
                if created or not basic_package.is_available:
                    basic_package.is_available = True
                    basic_package.save()
                available_packages = Package.objects.filter(id=basic_package.id)
                if not temp_booking.package:
                    temp_booking.package = basic_package
                    temp_booking.total_package_price = calculate_package_price(
                        package_instance=basic_package,
                        pickup_date=temp_booking.pickup_date,
                        return_date=temp_booking.return_date,
                        pickup_time=temp_booking.pickup_time,
                        return_time=temp_booking.return_time,
                        hire_settings=hire_settings
                    )
                    temp_booking.save()
                    messages.info(request, "No custom packages found, a default 'Basic Hire' package has been selected.")
            else:
                available_packages = all_available_packages

                if not temp_booking.package:
                    basic_package_option = all_available_packages.filter(name="Basic Hire").first()
                    if basic_package_option:
                        temp_booking.package = basic_package_option
                        temp_booking.total_package_price = calculate_package_price(
                            package_instance=basic_package_option,
                            pickup_date=temp_booking.pickup_date,
                            return_date=temp_booking.return_date,
                            pickup_time=temp_booking.pickup_time,
                            return_time=temp_booking.return_time,
                            hire_settings=hire_settings
                        )
                        temp_booking.save()
                    elif all_available_packages.exists():
                        temp_booking.package = all_available_packages.first()
                        temp_booking.total_package_price = calculate_package_price(
                            package_instance=all_available_packages.first(),
                            pickup_date=temp_booking.pickup_date,
                            return_date=temp_booking.return_date,
                            pickup_time=temp_booking.pickup_time,
                            return_time=temp_booking.return_time,
                            hire_settings=hire_settings
                        )
                        temp_booking.save()
        else:
            if temp_booking.package:
                temp_booking.package = None
                temp_booking.total_package_price = Decimal('0.00')
                temp_booking.save()

        for package_obj in available_packages:
            package_obj.package_price = calculate_package_price(
                package_instance=package_obj,
                pickup_date=temp_booking.pickup_date,
                return_date=temp_booking.return_date,
                pickup_time=temp_booking.pickup_time,
                return_time=temp_booking.return_time,
                hire_settings=hire_settings
            )

        all_addons_for_form = AddOn.objects.all()
        for addon_obj in all_addons_for_form:
            addon_obj.cost = calculate_addon_price(
                addon_instance=addon_obj,
                quantity=1,
                pickup_date=temp_booking.pickup_date,
                return_date=temp_booking.return_date,
                pickup_time=temp_booking.pickup_time,
                return_time=temp_booking.return_time,
                hire_settings=hire_settings
            )

        initial_data = {}
        if temp_booking.package:
            initial_data['package'] = temp_booking.package.id
        
        for temp_addon in temp_booking.temp_booking_addons.all():
            if all_addons_for_form.filter(id=temp_addon.addon.id).exists():
                initial_data[f'addon_{temp_addon.addon.id}_selected'] = True
                initial_data[f'addon_{temp_addon.addon.id}_quantity'] = temp_addon.quantity

        form = Step3AddOnsPackagesForm(
            initial=initial_data,
            available_packages=available_packages,
            available_addons=all_addons_for_form,
            selected_package_instance=temp_booking.package,
            temp_booking=temp_booking,
            hire_settings=hire_settings
        )

        context = {
            'temp_booking': temp_booking,
            'form': form,
            'available_packages': available_packages,
            'all_active_addons': AddOn.objects.filter(is_available=True),
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
        all_addons_for_form = AddOn.objects.all()

        selected_package_id = request.POST.get('package')
        selected_package_instance_for_form = None
        if selected_package_id:
            try:
                selected_package_instance_for_form = Package.objects.get(id=selected_package_id)
            except Package.DoesNotExist:
                pass

        form = Step3AddOnsPackagesForm(
            request.POST,
            available_packages=available_packages,
            available_addons=all_addons_for_form,
            selected_package_instance=selected_package_instance_for_form,
            temp_booking=temp_booking,
            hire_settings=hire_settings
        )

        if form.is_valid():
            selected_package = form.cleaned_data.get('selected_package')
            selected_addons_data = form.cleaned_data.get('selected_addons', [])

            if selected_package:
                temp_booking.package = selected_package
                temp_booking.total_package_price = calculate_package_price(
                    package_instance=selected_package,
                    pickup_date=temp_booking.pickup_date,
                    return_date=temp_booking.return_date,
                    pickup_time=temp_booking.pickup_time,
                    return_time=temp_booking.return_time,
                    hire_settings=hire_settings
                )
            else:
                temp_booking.package = None
                temp_booking.total_package_price = Decimal('0.00')

            temp_booking.temp_booking_addons.all().delete()

            total_addons_price_calculated = Decimal('0.00')

            for item in selected_addons_data:
                addon = item['addon']
                quantity = item['quantity']
                
                pickup_datetime = datetime.datetime.combine(temp_booking.pickup_date, temp_booking.pickup_time)
                return_datetime = datetime.datetime.combine(temp_booking.return_date, temp_booking.return_time)
                total_duration_seconds = (return_datetime - pickup_datetime).total_seconds()
                total_duration_hours = Decimal(total_duration_seconds / 3600).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
                is_same_day_hire = temp_booking.pickup_date == temp_booking.return_date

                single_unit_booked_price = _calculate_price_by_strategy(
                    total_duration_hours=total_duration_hours,
                    daily_rate=addon.daily_cost,
                    hourly_rate=addon.hourly_cost,
                    pricing_strategy=hire_settings.hire_pricing_strategy,
                    excess_hours_margin=hire_settings.excess_hours_margin,
                    is_same_day_hire=is_same_day_hire
                )

                TempBookingAddOn.objects.create(
                    temp_booking=temp_booking,
                    addon=addon,
                    quantity=quantity,
                    booked_addon_price=single_unit_booked_price
                )
                
                calculated_addon_total_price_for_item = single_unit_booked_price * Decimal(str(quantity))
                total_addons_price_calculated += calculated_addon_total_price_for_item

            temp_booking.total_addons_price = total_addons_price_calculated

            prices = calculate_booking_grand_total(temp_booking, hire_settings)
            
            temp_booking.total_hire_price = prices['motorcycle_price'] 
            temp_booking.total_package_price = prices['package_price']
            temp_booking.total_addons_price = prices['addons_total_price']
            temp_booking.grand_total = prices['grand_total']
            temp_booking.save()

            messages.success(request, "Add-ons and packages updated successfully.")
            if request.user.is_authenticated:
                return redirect('hire:step4_has_account')
            else:
                return redirect('hire:step4_no_account')
        else:
            messages.error(request, "Please correct the errors below.")
            
            for package_obj in available_packages:
                package_obj.package_price = calculate_package_price(
                    package_instance=package_obj,
                    pickup_date=temp_booking.pickup_date,
                    return_date=temp_booking.return_date,
                    pickup_time=temp_booking.pickup_time,
                    return_time=temp_booking.return_time,
                    hire_settings=hire_settings
                )

            for addon_obj in all_addons_for_form:
                addon_obj.cost = calculate_addon_price(
                    addon_instance=addon_obj,
                    quantity=1,
                    pickup_date=temp_booking.pickup_date,
                    return_date=temp_booking.return_date,
                    pickup_time=temp_booking.pickup_time,
                    return_time=temp_booking.return_time,
                    hire_settings=hire_settings
                )

            context = {
                'temp_booking': temp_booking,
                'form': form,
                'available_packages': available_packages,
                'all_active_addons': AddOn.objects.filter(is_available=True),
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
