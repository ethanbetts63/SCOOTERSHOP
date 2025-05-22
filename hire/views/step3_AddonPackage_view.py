# hire/views/step3_AddonPackage_view.py

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.utils import timezone
import datetime
from decimal import Decimal

from inventory.models import Motorcycle
from ..models import AddOn, Package, TempHireBooking, HireBooking, TempBookingAddOn
from ..forms.step3_AddonPackage_form import Step3AddOnsPackagesForm
from ..views.utils import calculate_hire_price, calculate_hire_duration_days
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

            if not self._is_motorcycle_available(motorcycle, temp_booking):
                messages.error(request, "The selected motorcycle is not available for your chosen dates/times or license type.")
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

        available_addons = AddOn.objects.none() # Initialize as empty QuerySet
        if hire_settings and hire_settings.add_ons_enabled:
            available_addons = AddOn.objects.filter(is_available=True)

        initial_data = {}
        if temp_booking.package:
            initial_data['package'] = temp_booking.package.id
        for temp_addon in temp_booking.temp_booking_addons.all():
            initial_data[f'addon_{temp_addon.addon.id}_selected'] = True
            initial_data[f'addon_{temp_addon.addon.id}_quantity'] = temp_addon.quantity

        form = Step3AddOnsPackagesForm(
            initial=initial_data,
            available_packages=available_packages,  # Pass QuerySet here
            available_addons=available_addons      # Pass QuerySet here
        )

        context = {
            'temp_booking': temp_booking,
            'form': form,
            'available_packages': available_packages, # For JS mapping, can be QuerySet
            'available_addons': available_addons,     # For JS mapping, can be QuerySet
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
        available_addons = AddOn.objects.filter(is_available=True)

        form = Step3AddOnsPackagesForm(
            request.POST,
            available_packages=available_packages,
            available_addons=available_addons
        )

        if form.is_valid():
            selected_package = form.cleaned_data.get('selected_package')
            selected_addons_data = form.cleaned_data.get('selected_addons', [])

            temp_booking.package = selected_package
            temp_booking.total_package_price = selected_package.package_price if selected_package else Decimal('0.00')

            temp_booking.temp_booking_addons.all().delete()

            total_addons_price = Decimal('0.00')
            hire_duration_days = calculate_hire_duration_days(
                temp_booking.pickup_date, temp_booking.return_date, temp_booking.pickup_time, temp_booking.return_time
            )

            for item in selected_addons_data:
                addon = item['addon']
                quantity = item['quantity']
                if not (selected_package and addon in selected_package.add_ons.all()):
                    TempBookingAddOn.objects.create(
                        temp_booking=temp_booking,
                        addon=addon,
                        quantity=quantity,
                        booked_addon_price=addon.cost
                    )
                    total_addons_price += (addon.cost * quantity * hire_duration_days)

            temp_booking.total_addons_price = total_addons_price
            temp_booking.grand_total = temp_booking.total_hire_price + temp_booking.total_package_price + temp_booking.total_addons_price
            temp_booking.save()

            messages.success(request, "Add-ons and packages updated successfully.")
            if request.user.is_authenticated:
                return redirect('hire:step4_has_account')
            else:
                return redirect('hire:step4_no_account')
        else:
            messages.error(request, "Please correct the errors below.")
            context = {
                'temp_booking': temp_booking,
                'form': form,
                'available_packages': available_packages,
                'available_addons': available_addons,
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

    def _is_motorcycle_available(self, motorcycle, temp_booking):
        if not temp_booking.pickup_date or not temp_booking.pickup_time or \
           not temp_booking.return_date or not temp_booking.return_time:
            messages.error(self.request, "Please select valid pickup and return dates/times first.")
            return False

        pickup_datetime = timezone.make_aware(
            datetime.datetime.combine(temp_booking.pickup_date, temp_booking.pickup_time)
        )
        return_datetime = timezone.make_aware(
            datetime.datetime.combine(temp_booking.return_date, temp_booking.return_time)
        )

        if return_datetime <= pickup_datetime:
            messages.error(self.request, "Return time must be after pickup time.")
            return False

        conflicting_bookings = HireBooking.objects.filter(
            motorcycle=motorcycle,
            pickup_date__lt=temp_booking.return_date,
            return_date__gt=temp_booking.pickup_date
        ).exists()

        if not temp_booking.has_motorcycle_license and int(motorcycle.engine_size) > 50:
             messages.error(self.request, "You require a full motorcycle license for this motorcycle.")
             return False

        return not conflicting_bookings