from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from hire.forms import Step4HasAccountForm
from hire.models import TempHireBooking, DriverProfile
from django.contrib import messages
from dashboard.models import HireSettings
from hire.hire_pricing import calculate_booking_grand_total
import uuid
from django.core.exceptions import ValidationError


class HasAccountView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        temp_booking = self._get_temp_booking(request)
        if not temp_booking:
            messages.error(
                request, "Your booking session has expired. Please start again."
            )
            return redirect("hire:step2_choose_bike")

        driver_profile_instance = None
        try:
            driver_profile_instance = DriverProfile.objects.get(user=request.user)
        except DriverProfile.DoesNotExist:
            driver_profile_instance = DriverProfile(user=request.user)

        form = Step4HasAccountForm(user=request.user, instance=driver_profile_instance, temp_booking=temp_booking)

        context = {
            "form": form,
            "temp_booking": temp_booking,
        }
        return render(request, "hire/step4_has_account.html", context)

    def post(self, request, *args, **kwargs):
        temp_booking = self._get_temp_booking(request)
        if not temp_booking:
            messages.error(
                request, "Your booking session has expired. Please start again."
            )
            return redirect("hire:step2_choose_bike")
        
        driver_profile_instance = None
        try:
            driver_profile_instance = DriverProfile.objects.get(user=request.user)
        except DriverProfile.DoesNotExist:
            driver_profile_instance = DriverProfile(user=request.user)


        form = Step4HasAccountForm(request.POST, request.FILES, user=request.user, instance=driver_profile_instance, temp_booking=temp_booking)

        if form.is_valid():
            driver_profile = form.save(commit=False)
            driver_profile.user = request.user
            
            try:
                driver_profile.full_clean()
                driver_profile.save()
            except ValidationError as e:
                for field, errors in e.message_dict.items():
                    for error in errors:
                        messages.error(request, f"Error in {field}: {error}")
                context = {
                    "form": form,
                    "temp_booking": temp_booking,
                }
                messages.error(request, "Please correct the errors below (model validation).")
                return render(request, "hire/step4_has_account.html", context)


            temp_booking.driver_profile = driver_profile
            
            hire_settings = HireSettings.objects.first()
            if hire_settings:
                calculated_prices = calculate_booking_grand_total(temp_booking, hire_settings)
                temp_booking.total_hire_price = calculated_prices['motorcycle_price']
                temp_booking.total_package_price = calculated_prices['package_price']
                temp_booking.total_addons_price = calculated_prices['addons_total_price']
                temp_booking.grand_total = calculated_prices['grand_total']
                temp_booking.deposit_amount = calculated_prices['deposit_amount']
                temp_booking.currency = calculated_prices['currency']
            else:
                messages.warning(request, "Hire settings not found. Cannot calculate accurate booking prices.")

            temp_booking.save()
            messages.success(request, "Driver details saved successfully.")
            return redirect("hire:step5_summary_payment_options")
        else:
            context = {
                "form": form,
                "temp_booking": temp_booking,
            }
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error in {field}: {error}")
            messages.error(request, "Please correct the errors below (form validation).")
            return render(request, "hire/step4_has_account.html", context)

    def _get_temp_booking(self, request):
        temp_booking_uuid_str = request.session.get("temp_booking_uuid")

        if temp_booking_uuid_str:
            try:
                lookup_uuid = uuid.UUID(temp_booking_uuid_str)
                temp_booking = TempHireBooking.objects.get(session_uuid=lookup_uuid)
                return temp_booking
            except TempHireBooking.DoesNotExist:
                return None
            except ValueError:
                return None
            except Exception as e: 
                return None
        
        return None
