# hire/views/step5_BookSumAndPaymentOptions_view.py

from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from decimal import Decimal # Import Decimal for precise calculations

from ..models import TempHireBooking
from dashboard.models import HireSettings
from ..forms.step5_BookSumAndPaymentOptions_form import PaymentOptionForm
from ..views.utils import *

class BookSumAndPaymentOptionsView(View):
    template_name = 'hire/step5_book_sum_and_payment_options.html'

    def get(self, request, *args, **kwargs):
        temp_booking = self._get_temp_booking(request)
        if not temp_booking:
            messages.error(request, "Your booking session has expired. Please start again.")
            return redirect('hire:step2_choose_bike')

        hire_settings = HireSettings.objects.first()
        if not hire_settings:
            messages.error(request, "Hire settings not found.")
            return redirect('home') # Or some appropriate error page

        form = PaymentOptionForm(temp_booking=temp_booking, hire_settings=hire_settings)

        context = {
            'temp_booking': temp_booking,
            'hire_settings': hire_settings,
            'form': form,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        temp_booking = self._get_temp_booking(request)
        if not temp_booking:
            messages.error(request, "Your booking session has expired. Please start again.")
            return redirect('hire:step2_choose_bike')

        hire_settings = HireSettings.objects.first()
        if not hire_settings:
            messages.error(request, "Hire settings not found.")
            return redirect('home') # Or some appropriate error page

        form = PaymentOptionForm(request.POST, temp_booking=temp_booking, hire_settings=hire_settings)

        if form.is_valid():
            payment_option = form.cleaned_data['payment_method']
            temp_booking.payment_option = payment_option # Correctly assign to the 'payment_option' field

            # --- Ensure grand_total and deposit_amount are calculated and saved ---
            # These values should ideally be calculated and saved in earlier steps
            # (e.g., after selecting add-ons/packages), but we'll ensure they are here
            # before proceeding to payment.

            # Recalculate grand_total if it's not already set or needs updating
            # This logic might be more complex depending on how your prices are derived.
            # For simplicity, assuming it's a sum of existing fields.
            # You might have a method on TempHireBooking like `calculate_grand_total()`
            if temp_booking.total_hire_price is None:
                temp_booking.total_hire_price = Decimal('0.00') # Default if not set
            if temp_booking.total_addons_price is None:
                temp_booking.total_addons_price = Decimal('0.00')
            if temp_booking.total_package_price is None:
                temp_booking.total_package_price = Decimal('0.00')

            # Ensure grand_total is set. If it's already correctly calculated in a prior step,
            # this line might not be strictly necessary, but it ensures it's available.
            temp_booking.grand_total = (
                temp_booking.total_hire_price +
                temp_booking.total_addons_price +
                temp_booking.total_package_price
            )

            # Calculate deposit_amount based on grand_total and hire_settings
            if hire_settings and hire_settings.deposit_percentage is not None:
                # Ensure deposit_percentage is a Decimal for accurate calculation
                deposit_percentage = Decimal(str(hire_settings.deposit_percentage)) / Decimal('100')
                temp_booking.deposit_amount = temp_booking.grand_total * deposit_percentage
                # Round to 2 decimal places for currency
                temp_booking.deposit_amount = temp_booking.deposit_amount.quantize(Decimal('0.01'))
            else:
                # Fallback if deposit_percentage is not set in HireSettings
                temp_booking.deposit_amount = Decimal('0.00') # Or a default deposit amount if applicable

            # Save the updated TempHireBooking instance
            temp_booking.save()

            # Redirect to the next step based on the payment option
            if payment_option == 'online_full' or payment_option == 'online_deposit':
                return redirect('hire:step6_payment_details') # To payment gateway details
            else:
                return redirect('hire:step6_payment_details') # For in-store, we might just confirm details

        else:
            context = {
                'temp_booking': temp_booking,
                'hire_settings': hire_settings,
                'form': form,
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

