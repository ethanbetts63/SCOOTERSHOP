import datetime
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.utils import timezone
from django.urls import reverse

from inventory.models import Motorcycle
from ..models import AddOn, Package, DriverProfile, HireBooking, BookingAddOn
from dashboard.models import HireSettings, BlockedHireDate

from ..forms.Admin_Hire_Booking_form import AdminHireBookingForm

from ..utils import get_overlapping_motorcycle_bookings
from ..hire_pricing import calculate_motorcycle_hire_price, calculate_addon_price, calculate_booking_grand_total

class AdminHireBookingView(View):
    template_name = 'hire/admin_hire_booking.html'

    def _get_context_data(self, request, form, booking_instance=None):
        hire_settings = HireSettings.objects.first()

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
                {'id': p.id, 'name': p.name, 'daily_cost': str(p.daily_cost), 'hourly_cost': str(p.hourly_cost)}
                for p in all_packages
            ],
            'addons_data': [
                {'id': a.id, 'daily_cost': str(a.daily_cost), 'hourly_cost': str(a.hourly_cost), 'min_quantity': a.min_quantity, 'max_quantity': a.max_quantity}
                for a in all_addons
            ],
            'driver_profiles_data': [
                {'id': dp.id, 'name': dp.name, 'email': dp.email}
                for dp in all_driver_profiles
            ],
            'default_daily_rate': str(hire_settings.default_daily_rate) if hire_settings and hire_settings.default_daily_rate is not None else "0.00",
            'default_hourly_rate': str(hire_settings.default_hourly_rate) if hire_settings and hire_settings.default_hourly_rate is not None else "0.00",
            'booking': booking_instance,
        }
        return context


    def get(self, request, pk=None, *args, **kwargs):
        booking_instance = None
        if pk:
            try:
                booking_instance = get_object_or_404(HireBooking, pk=pk)
                form = AdminHireBookingForm(instance=booking_instance, hire_settings=HireSettings.objects.first())
                messages.info(request, f"Editing Hire Booking: {booking_instance.booking_reference}")
            except Exception as e:
                messages.error(request, f"Error loading booking for edit: {e}")
                return redirect('dashboard:hire_bookings')
        else:
            form = AdminHireBookingForm(hire_settings=HireSettings.objects.first())
            messages.info(request, "Creating New Hire Booking")

        if 'last_overlap_attempt' in request.session:
            del request.session['last_overlap_attempt']

        context = self._get_context_data(request, form, booking_instance)
        return render(request, self.template_name, context)

    def post(self, request, pk=None, *args, **kwargs):
        booking_instance = None
        if pk:
            try:
                booking_instance = get_object_or_404(HireBooking, pk=pk)
                form = AdminHireBookingForm(request.POST, instance=booking_instance, hire_settings=HireSettings.objects.first())
            except Exception as e:
                messages.error(request, f"Error loading booking for update: {e}")
                return redirect('dashboard:hire_bookings')
        else:
            form = AdminHireBookingForm(request.POST, hire_settings=HireSettings.objects.first())

        hire_settings = HireSettings.objects.first()

        if form.is_valid():
            pickup_date = form.cleaned_data['pick_up_date']
            pickup_time = form.cleaned_data['pick_up_time']
            return_date = form.cleaned_data['return_date']
            return_time = form.cleaned_data['return_time']
            motorcycle = form.cleaned_data['motorcycle']

            pickup_datetime_for_identifier = timezone.make_aware(datetime.datetime.combine(pickup_date, pickup_time))
            return_datetime_for_identifier = timezone.make_aware(datetime.datetime.combine(return_date, return_time))

            current_overlap_identifier = (
                motorcycle.id,
                pickup_datetime_for_identifier.isoformat(),
                return_datetime_for_identifier.isoformat()
            )
            
            last_overlap_attempt_raw = request.session.get('last_overlap_attempt')
            last_overlap_attempt = tuple(last_overlap_attempt_raw) if isinstance(last_overlap_attempt_raw, list) else last_overlap_attempt_raw
            
            exclude_booking_id = booking_instance.id if booking_instance else None
            actual_overlaps = get_overlapping_motorcycle_bookings(
                motorcycle,
                pickup_date,
                pickup_time,
                return_date,
                return_time,
                exclude_booking_id=exclude_booking_id
            )
            
            allow_booking_creation_or_update = True
            if actual_overlaps:
                if last_overlap_attempt == current_overlap_identifier:
                    messages.info(request, "Overlap warning overridden. Proceeding despite overlap.")
                    if 'last_overlap_attempt' in request.session:
                        del request.session['last_overlap_attempt']
                else:
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
                    allow_booking_creation_or_update = False
            else:
                if 'last_overlap_attempt' in request.session:
                    del request.session['last_overlap_attempt']

            if not allow_booking_creation_or_update:
                context = self._get_context_data(request, form, booking_instance)
                return render(request, self.template_name, context)

            booked_daily_rate = form.cleaned_data['booked_daily_rate']
            booked_hourly_rate = form.cleaned_data['booked_hourly_rate']
            selected_package = form.cleaned_data.get('selected_package_instance')
            selected_addons_data = form.cleaned_data.get('selected_addons_data', [])
            driver_profile = form.cleaned_data['driver_profile']
            is_international_booking = not driver_profile.is_australian_resident
            currency = form.cleaned_data['currency']
            payment_method = form.cleaned_data['payment_method']
            payment_status = form.cleaned_data['payment_status']
            status = form.cleaned_data['status']
            internal_notes = form.cleaned_data.get('internal_notes')

            class TempBookingLike:
                def __init__(self, motorcycle, pickup_date, pickup_time, return_date, return_time, package, addons_data):
                    self.motorcycle = motorcycle
                    self.pickup_date = pickup_date
                    self.pickup_time = pickup_time
                    self.return_date = return_date
                    self.return_time = return_time
                    self.package = package
                    self._addons_data = addons_data

                def temp_booking_addons(self):
                    class AddonProxy:
                        def __init__(self, addon, quantity):
                            self.addon = addon
                            self.quantity = quantity
                    return [AddonProxy(item['addon'], item['quantity']) for item in self._addons_data]

                def __bool__(self):
                    return True

            temp_booking_for_pricing = TempBookingLike(
                motorcycle=motorcycle,
                pickup_date=pickup_date,
                pickup_time=pickup_time,
                return_date=return_date,
                return_time=return_time,
                package=selected_package,
                addons_data=selected_addons_data
            )

            calculated_prices = calculate_booking_grand_total(temp_booking_for_pricing, hire_settings)

            total_hire_price = calculated_prices['motorcycle_price']
            total_addons_price = calculated_prices['addons_total_price']
            total_package_price = calculated_prices['package_price']
            grand_total = calculated_prices['grand_total']

            amount_paid = Decimal('0.00')
            if payment_status == 'paid':
                amount_paid = grand_total
            elif payment_status == 'deposit_paid' and hire_settings and hire_settings.deposit_percentage is not None:
                deposit_percentage = Decimal(str(hire_settings.deposit_percentage)) / Decimal('100')
                amount_paid = grand_total * deposit_percentage
                amount_paid = amount_paid.quantize(Decimal('0.01'))

            deposit_amount = Decimal('0.00')
            if hire_settings and hire_settings.deposit_percentage is not None:
                deposit_percentage = Decimal(str(hire_settings.deposit_percentage)) / Decimal('100')
                deposit_amount = grand_total * deposit_percentage
                deposit_amount = deposit_amount.quantize(Decimal('0.01'))


            try:
                if booking_instance:
                    booking_instance.motorcycle = motorcycle
                    booking_instance.driver_profile = driver_profile
                    booking_instance.pickup_date = pickup_date
                    booking_instance.pickup_time = pickup_time
                    booking_instance.return_date = return_date
                    booking_instance.return_time = return_time
                    booking_instance.booked_daily_rate = booked_daily_rate
                    booking_instance.booked_hourly_rate = booked_hourly_rate
                    booking_instance.total_hire_price = total_hire_price
                    booking_instance.total_addons_price = total_addons_price
                    booking_instance.total_package_price = total_package_price
                    booking_instance.grand_total = grand_total
                    booking_instance.deposit_amount = deposit_amount
                    booking_instance.amount_paid = amount_paid
                    booking_instance.payment_status = payment_status
                    booking_instance.payment_method = payment_method
                    booking_instance.status = status
                    booking_instance.currency = currency
                    booking_instance.internal_notes = internal_notes
                    booking_instance.is_international_booking = is_international_booking
                    booking_instance.package = selected_package
                    booking_instance.save()

                    booking_instance.booking_addons.all().delete()
                    for item in selected_addons_data:
                        BookingAddOn.objects.create(
                            booking=booking_instance,
                            addon=item['addon'],
                            quantity=item['quantity'],
                            booked_addon_price=item['price']
                        )
                    messages.success(request, f"Hire Booking {booking_instance.booking_reference} updated successfully!")
                else:
                    hire_booking = HireBooking.objects.create(
                        motorcycle=motorcycle,
                        driver_profile=driver_profile,
                        pickup_date=pickup_date,
                        pickup_time=pickup_time,
                        return_date=return_date,
                        return_time=return_time,
                        booked_daily_rate=booked_daily_rate,
                        booked_hourly_rate=booked_hourly_rate,
                        total_hire_price=total_hire_price,
                        total_addons_price=total_addons_price,
                        total_package_price=total_package_price,
                        grand_total=grand_total,
                        deposit_amount=deposit_amount,
                        amount_paid=amount_paid,
                        payment_status=payment_status,
                        payment_method=payment_method,
                        status=status,
                        currency=currency,
                        internal_notes=internal_notes,
                        is_international_booking=is_international_booking,
                        package=selected_package,
                    )
                    booking_instance = hire_booking

                    for item in selected_addons_data:
                        BookingAddOn.objects.create(
                            booking=hire_booking,
                            addon=item['addon'],
                            quantity=item['quantity'],
                            booked_addon_price=item['price']
                        )
                    messages.success(request, f"Hire Booking {hire_booking.booking_reference} created successfully!")

                return redirect('dashboard:hire_booking_details', pk=booking_instance.pk)

            except Exception as e:
                messages.error(request, f"An error occurred while saving the booking: {e}")
                context = self._get_context_data(request, form, booking_instance)
                return render(request, self.template_name, context)

        else:
            context = self._get_context_data(request, form, booking_instance)
            messages.error(request, "Please correct the errors below.")
            return render(request, self.template_name, context)
