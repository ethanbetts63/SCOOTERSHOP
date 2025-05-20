# hire/views/step4_NoAccount_view.py
from django.shortcuts import render, redirect
from django.views import View
from hire.forms import Step4NoAccountForm
from hire.models import TempHireBooking, DriverProfile
from django.contrib import messages
from django.urls import reverse

class NoAccountView(View):
    """
    Handles Step 4 of the hire process for anonymous users.
    - Retrieves the TempHireBooking instance from the session.
    - Displays the Step4NoAccountForm to collect driver details.
    - Processes the form submission to create a new DriverProfile.
    - Saves the DriverProfile to the TempHireBooking.
    - Redirects to the next step (Step 5).
    """

    def get(self, request, *args, **kwargs):
        """
        Displays the Step4NoAccountForm.
        """
        # 1. Retrieve TempHireBooking
        try:
            temp_booking_id = request.session['temp_booking_id']
            temp_booking = TempHireBooking.objects.get(session_uuid=temp_booking_id)
        except (KeyError, TempHireBooking.DoesNotExist):
            messages.error(request, "Your booking session has expired. Please start again.")
            return redirect('hire:step1')  # Redirect to the first step

        form = Step4NoAccountForm()
        return render(request, 'hire/step4_no_account.html', {'form': form, 'temp_booking': temp_booking})

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
            return redirect('hire:step1')

        form = Step4NoAccountForm(request.POST, request.FILES)
        if form.is_valid():
            # 2. Create a new DriverProfile
            driver_profile = DriverProfile.objects.create(
                name=form.cleaned_data['name'],
                email=form.cleaned_data['email'],
                phone=form.cleaned_data['phone'],
                address=form.cleaned_data['address'],
                date_of_birth=form.cleaned_data['date_of_birth'],
                is_australian_resident=form.cleaned_data['is_australian_resident'],
                license_number=form.cleaned_data['license_number'],
                license_issuing_country=form.cleaned_data['license_issuing_country'],
                license_expiry_date=form.cleaned_data['license_expiry_date'],
                license_photo=form.cleaned_data['license_photo'],
                international_license_photo=form.cleaned_data['international_license_photo'],
                passport_photo=form.cleaned_data['passport_photo'],
                passport_number=form.cleaned_data['passport_number'],
                passport_expiry_date=form.cleaned_data['passport_expiry_date'],
            )

            # 3. Save DriverProfile to TempHireBooking
            temp_booking.driver_profile = driver_profile
            temp_booking.save()

            # 4. Redirect to next step (Step 5)
            return redirect('hire:step5')  # Replace with your actual URL name for Step 5
        else:
            return render(request, 'hire/step4_no_account.html', {'form': form, 'temp_booking': temp_booking})