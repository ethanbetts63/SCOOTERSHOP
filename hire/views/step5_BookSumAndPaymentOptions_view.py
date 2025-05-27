# hire/views/step5_BookSumAndPaymentOptions_view.py

from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from decimal import Decimal # Import Decimal for precise calculations

from ..models import TempHireBooking
from dashboard.models import HireSettings
from ..forms.step5_BookSumAndPaymentOptions_form import PaymentOptionForm
from ..utils import *
# Import the new centralized pricing function
from ..hire_pricing import calculate_booking_grand_total

class BookSumAndPaymentOptionsView(View):
    # FIX: Corrected the template name to match the actual file name
    template_name = 'hire/step5_book_sum_and_payment_options.html'

    def get(self, request, *args, **kwargs):
        temp_booking = self._get_temp_booking(request)
        if not temp_booking:
            messages.error(request, "Your booking session has expired. Please start again.")
            return redirect('hire:step2_choose_bike')

        hire_settings = HireSettings.objects.first()
        if not hire_settings:
            messages.error(request, "Hire settings not found.")
            return redirect('core:index') # Or some appropriate error page

        # Recalculate all booking prices to ensure they are up-to-date
        # This acts as a safeguard in case previous steps didn't save correctly
        # or if the user navigates directly to this step.
        calculated_prices = calculate_booking_grand_total(temp_booking, hire_settings)
        temp_booking.total_hire_price = calculated_prices['motorcycle_price']
        temp_booking.total_package_price = calculated_prices['package_price']
        temp_booking.total_addons_price = calculated_prices['addons_total_price']
        temp_booking.grand_total = calculated_prices['grand_total']

        # Calculate deposit_amount based on the freshly calculated grand_total
        if hire_settings and hire_settings.deposit_percentage is not None:
            deposit_percentage = Decimal(str(hire_settings.deposit_percentage)) / Decimal('100')
            temp_booking.deposit_amount = temp_booking.grand_total * deposit_percentage
            temp_booking.deposit_amount = temp_booking.deposit_amount.quantize(Decimal('0.01'))
        else:
            temp_booking.deposit_amount = Decimal('0.00')

        # Save the updated prices to the temporary booking before rendering the form
        temp_booking.save()

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
            return redirect('core:index') # Or some appropriate error page

        form = PaymentOptionForm(request.POST, temp_booking=temp_booking, hire_settings=hire_settings)

        if form.is_valid():
            payment_option = form.cleaned_data['payment_method']
            temp_booking.payment_option = payment_option

            # --- Recalculate grand_total and other prices using the centralized function ---
            # This ensures the prices are accurate based on the latest booking data
            # and the current pricing strategies, just before saving and redirecting.
            calculated_prices = calculate_booking_grand_total(temp_booking, hire_settings)
            temp_booking.total_hire_price = calculated_prices['motorcycle_price']
            temp_booking.total_package_price = calculated_prices['package_price']
            temp_booking.total_addons_price = calculated_prices['addons_total_price']
            temp_booking.grand_total = calculated_prices['grand_total']

            # Calculate deposit_amount based on the freshly calculated grand_total
            if hire_settings and hire_settings.deposit_percentage is not None:
                deposit_percentage = Decimal(str(hire_settings.deposit_percentage)) / Decimal('100')
                temp_booking.deposit_amount = temp_booking.grand_total * deposit_percentage
                temp_booking.deposit_amount = temp_booking.deposit_amount.quantize(Decimal('0.01'))
            else:
                temp_booking.deposit_amount = Decimal('0.00') # Fallback if deposit_percentage is not set

            # Save the updated TempHireBooking instance with all calculated prices
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
