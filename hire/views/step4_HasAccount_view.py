# hire/views/step4_HasAccount_view.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin  # Ensure user is logged in
from hire.forms import Step4HasAccountForm
from hire.models import TempHireBooking
from users.models import User
from hire.models import DriverProfile
from dashboard.models import HireSettings
from django.contrib import messages  # For displaying messages to the user
from django.urls import reverse

class HasAccountView(LoginRequiredMixin, View):
    """
    Handles Step 4 of the hire process for logged-in users.
    - Retrieves the TempHireBooking instance from the session.
    - Pre-fills the form with the user's data and existing DriverProfile (if any).
    - Processes the form submission to either create a new DriverProfile or update an existing one.
    - Saves the DriverProfile to the TempHireBooking.
    - Redirects to the next step (Step 5).
    """

    def get(self, request, *args, **kwargs):
        """
        Displays the Step4HasAccountForm, pre-filled with user data.
        """
        # 1. Retrieve TempHireBooking
        try:
            temp_booking_id = request.session['temp_booking_id']
            temp_booking = TempHireBooking.objects.get(session_uuid=temp_booking_id)
        except (KeyError, TempHireBooking.DoesNotExist):
            # Handle case where temp booking doesn't exist (e.g., session expired)
            messages.error(request, "Your booking session has expired. Please start again.")
            return redirect('hire:step2_choose_bike')  # Redirect to the first step

        # 2. Get or create DriverProfile
        driver_profile, created = DriverProfile.objects.get_or_create(user=request.user)

        # 3. Populate form initial data
        initial_data = {
            'name': driver_profile.name if driver_profile.name else request.user.get_full_name(),
            'email': driver_profile.email if driver_profile.email else request.user.email,
            'phone': driver_profile.phone if driver_profile.phone else '',
            'address': driver_profile.address if driver_profile.address else '',
            'date_of_birth': driver_profile.date_of_birth if driver_profile.date_of_birth else None,
            'is_australian_resident': driver_profile.is_australian_resident if driver_profile.is_australian_resident else False,
            'license_number': driver_profile.license_number if driver_profile.license_number else '',
            'license_issuing_country': driver_profile.license_issuing_country if driver_profile.license_issuing_country else '',
            'license_expiry_date': driver_profile.license_expiry_date if driver_profile.license_expiry_date else None,
            'license_photo': driver_profile.license_photo if driver_profile.license_photo else None,
            'international_license_photo': driver_profile.international_license_photo if driver_profile.international_license_photo else None,
            'passport_photo': driver_profile.passport_photo if driver_profile.passport_photo else None,
            'passport_number': driver_profile.passport_number if driver_profile.passport_number else '',
            'passport_expiry_date': driver_profile.passport_expiry_date if driver_profile.passport_expiry_date else None,
        }

        form = Step4HasAccountForm(initial=initial_data)
        return render(request, 'hire/step4_has_account.html', {'form': form, 'temp_booking': temp_booking})

    def post(self, request, *args, **kwargs):
        """
        Handles form submission, validates data, and saves the DriverProfile.
        """
        # 1. Retrieve TempHireBooking
        try:
            temp_booking_id = request.session['temp_booking_id']
            temp_booking = TempHireBooking.objects.get(session_uuid=temp_booking_id)
        except (KeyError, TempHireBooking.DoesNotExist):
            messages.error(request, "Your booking session has expired. Please start again.")
            return redirect('hire:step2_choose_bike')

        form = Step4HasAccountForm(request.POST, request.FILES)  # Include request.FILES for file uploads
        if form.is_valid():
            # 2. Get or create DriverProfile
            driver_profile, created = DriverProfile.objects.get_or_create(user=request.user)

            # 3. Update DriverProfile
            driver_profile.name = form.cleaned_data['name']
            driver_profile.email = form.cleaned_data['email']
            driver_profile.phone = form.cleaned_data['phone']
            driver_profile.address = form.cleaned_data['address']
            driver_profile.date_of_birth = form.cleaned_data['date_of_birth']
            driver_profile.is_australian_resident = form.cleaned_data['is_australian_resident']
            driver_profile.license_number = form.cleaned_data['license_number']
            driver_profile.license_issuing_country = form.cleaned_data['license_issuing_country']
            driver_profile.license_expiry_date = form.cleaned_data['license_expiry_date']
            driver_profile.license_photo = form.cleaned_data['license_photo']
            driver_profile.international_license_photo = form.cleaned_data['international_license_photo']
            driver_profile.passport_photo = form.cleaned_data['passport_photo']
            driver_profile.passport_number = form.cleaned_data['passport_number']
            driver_profile.passport_expiry_date = form.cleaned_data['passport_expiry_date']
            driver_profile.save()

            # 4. Save DriverProfile to TempHireBooking
            temp_booking.driver_profile = driver_profile
            temp_booking.save()

            # 5. Redirect to next step (Step 5)
            return redirect('hire:step5_summary_payment_options') 
        else:
            return render(request, 'hire/step4_has_account.html', {'form': form, 'temp_booking': temp_booking})