from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from hire.forms import Step4HasAccountForm
from hire.models import TempHireBooking, DriverProfile
from django.contrib import messages
from dashboard.models import HireSettings # Import HireSettings
from hire.hire_pricing import calculate_booking_grand_total # Import the new pricing function
import uuid # Import uuid module
from django.core.exceptions import ValidationError # Import ValidationError for model clean errors


class HasAccountView(LoginRequiredMixin, View):
    """
    Handles Step 4 for logged-in users.
    Ensures driver profile details are saved and calculates/updates booking prices
    before proceeding to the summary and payment options.
    """

    def get(self, request, *args, **kwargs):
        print(f"DEBUG: HasAccountView GET - User: {request.user}, Session Key: {request.session.session_key}")
        print(f"DEBUG: HasAccountView GET - Full session data: {dict(request.session)}")

        temp_booking = self._get_temp_booking(request)
        if not temp_booking:
            messages.error(
                request, "Your booking session has expired. Please start again."
            )
            return redirect("hire:step2_choose_bike")

        print(f"DEBUG: HasAccountView GET - temp_booking.driver_profile: {temp_booking.driver_profile}")

        driver_profile_instance = None
        try:
            driver_profile_instance = DriverProfile.objects.get(user=request.user)
            print(f"DEBUG: HasAccountView GET - Retrieved existing DriverProfile: {driver_profile_instance}")
        except DriverProfile.DoesNotExist:
            driver_profile_instance = DriverProfile(user=request.user)
            print("DEBUG: HasAccountView GET - Created new unsaved DriverProfile instance.")

        form = Step4HasAccountForm(user=request.user, instance=driver_profile_instance, temp_booking=temp_booking)

        context = {
            "form": form,
            "temp_booking": temp_booking,
        }
        return render(request, "hire/step4_has_account.html", context)

    def post(self, request, *args, **kwargs):
        print(f"DEBUG: HasAccountView POST - User: {request.user}, Session Key: {request.session.session_key}")
        print(f"DEBUG: HasAccountView POST - Full session data: {dict(request.session)}")
        print(f"DEBUG: HasAccountView POST - Request POST data: {request.POST}")
        print(f"DEBUG: HasAccountView POST - Request FILES data: {request.FILES}")

        temp_booking = self._get_temp_booking(request)
        if not temp_booking:
            messages.error(
                request, "Your booking session has expired. Please start again."
            )
            return redirect("hire:step2_choose_bike")

        print(f"DEBUG: HasAccountView POST - temp_booking.driver_profile: {temp_booking.driver_profile}")
        
        driver_profile_instance = None
        try:
            driver_profile_instance = DriverProfile.objects.get(user=request.user)
            print(f"DEBUG: HasAccountView POST - Retrieved existing DriverProfile for POST: {driver_profile_instance}")
        except DriverProfile.DoesNotExist:
            driver_profile_instance = DriverProfile(user=request.user)
            print("DEBUG: HasAccountView POST - Created new unsaved DriverProfile instance for POST.")


        form = Step4HasAccountForm(request.POST, request.FILES, user=request.user, instance=driver_profile_instance, temp_booking=temp_booking)
        print(f"DEBUG: HasAccountView POST - Form initialized with data and files.")

        if form.is_valid():
            print("DEBUG: HasAccountView POST - Form is VALID.")
            driver_profile = form.save(commit=False)
            driver_profile.user = request.user
            
            # Attempt to save the driver profile and catch model-level validation errors
            try:
                driver_profile.full_clean() # Call model's clean method
                driver_profile.save()
                print(f"DEBUG: HasAccountView POST - DriverProfile saved: {driver_profile}")
            except ValidationError as e:
                print(f"ERROR: HasAccountView POST - Model ValidationError during driver_profile save: {e.message_dict}")
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
            print(f"DEBUG: HasAccountView POST - temp_booking.driver_profile after setting: {temp_booking.driver_profile}")
            
            hire_settings = HireSettings.objects.first()
            if hire_settings:
                calculated_prices = calculate_booking_grand_total(temp_booking, hire_settings)
                temp_booking.total_hire_price = calculated_prices['motorcycle_price']
                temp_booking.total_package_price = calculated_prices['package_price']
                temp_booking.total_addons_price = calculated_prices['addons_total_price']
                temp_booking.grand_total = calculated_prices['grand_total']
                temp_booking.deposit_amount = calculated_prices['deposit_amount']
                temp_booking.currency = calculated_prices['currency'] # Added currency update
                print(f"DEBUG: HasAccountView POST - Updated temp_booking prices: {calculated_prices}")
            else:
                messages.warning(request, "Hire settings not found. Cannot calculate accurate booking prices.")
                print("WARNING: Hire settings not found. Cannot calculate accurate booking prices.")

            temp_booking.save()
            print("DEBUG: HasAccountView POST - TempHireBooking saved with updated driver profile and prices.")
            messages.success(request, "Driver details saved successfully.")
            return redirect("hire:step5_summary_payment_options")
        else:
            print("DEBUG: HasAccountView POST - Form is INVALID.")
            print(f"DEBUG: HasAccountView POST - Form errors: {form.errors.as_json()}")
            context = {
                "form": form,
                "temp_booking": temp_booking,
            }
            # Add form errors to messages
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error in {field}: {error}")
            messages.error(request, "Please correct the errors below (form validation).")
            return render(request, "hire/step4_has_account.html", context)

    def _get_temp_booking(self, request):
        temp_booking_uuid_str = request.session.get("temp_booking_uuid")
        print(f"DEBUG: _get_temp_booking - Retrieved 'temp_booking_uuid' from request.session: '{temp_booking_uuid_str}' (type: {type(temp_booking_uuid_str)})")

        if temp_booking_uuid_str:
            try:
                # Ensure the retrieved value is a valid UUID format before querying
                lookup_uuid = uuid.UUID(temp_booking_uuid_str)
                temp_booking = TempHireBooking.objects.get(session_uuid=lookup_uuid)
                print(f"DEBUG: _get_temp_booking - Found temp_booking (ID: {temp_booking.id}) for session_uuid: {lookup_uuid}")
                return temp_booking
            except TempHireBooking.DoesNotExist:
                print(f"DEBUG: _get_temp_booking - TempHireBooking.DoesNotExist for session_uuid: {lookup_uuid if 'lookup_uuid' in locals() else temp_booking_uuid_str}")
                return None
            except ValueError:
                # This will catch cases where temp_booking_uuid_str is not a valid UUID string
                print(f"DEBUG: _get_temp_booking - ValueError: '{temp_booking_uuid_str}' is not a valid UUID string.")
                return None
            except Exception as e: 
                print(f"DEBUG: _get_temp_booking - An unexpected error occurred during temp_booking lookup: {e} (session_uuid_str: '{temp_booking_uuid_str}')")
                return None
        
        print("DEBUG: _get_temp_booking - 'temp_booking_uuid' not found in request.session or is empty.")
        return None

