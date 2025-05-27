# hire/views/step5_BookSumAndPaymentOptions_view.py

from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from decimal import Decimal

from ..models import TempHireBooking
from dashboard.models import HireSettings
from ..forms.step5_BookSumAndPaymentOptions_form import PaymentOptionForm
from ..utils import is_motorcycle_available
from ..hire_pricing import calculate_booking_grand_total
from hire.temp_hire_converter import convert_temp_to_hire_booking

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
            return redirect('core:index')

        calculated_prices = calculate_booking_grand_total(temp_booking, hire_settings)
        temp_booking.total_hire_price = calculated_prices['motorcycle_price']
        temp_booking.total_package_price = calculated_prices['package_price']
        temp_booking.total_addons_price = calculated_prices['addons_total_price']
        temp_booking.grand_total = calculated_prices['grand_total']

        if hire_settings and hire_settings.deposit_percentage is not None:
            deposit_percentage = Decimal(str(hire_settings.deposit_percentage)) / Decimal('100')
            temp_booking.deposit_amount = temp_booking.grand_total * deposit_percentage
            temp_booking.deposit_amount = temp_booking.deposit_amount.quantize(Decimal('0.01'))
        else:
            temp_booking.deposit_amount = Decimal('0.00')

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
            return redirect('core:index')

        form = PaymentOptionForm(request.POST, temp_booking=temp_booking, hire_settings=hire_settings)

        if form.is_valid():
            payment_option = form.cleaned_data['payment_method']
            temp_booking.payment_option = payment_option

            calculated_prices = calculate_booking_grand_total(temp_booking, hire_settings)
            temp_booking.total_hire_price = calculated_prices['motorcycle_price']
            temp_booking.total_package_price = calculated_prices['package_price']
            temp_booking.total_addons_price = calculated_prices['addons_total_price']
            temp_booking.grand_total = calculated_prices['grand_total']

            if hire_settings and hire_settings.deposit_percentage is not None:
                deposit_percentage = Decimal(str(hire_settings.deposit_percentage)) / Decimal('100')
                temp_booking.deposit_amount = temp_booking.grand_total * deposit_percentage
                temp_booking.deposit_amount = temp_booking.deposit_amount.quantize(Decimal('0.01'))
            else:
                temp_booking.deposit_amount = Decimal('0.00')

            temp_booking.save()

            if not is_motorcycle_available(request, temp_booking.motorcycle, temp_booking):
                messages.error(request, "The selected motorcycle is no longer available for the chosen dates and times. Please select another motorcycle.")
                return redirect('hire:step2_choose_bike')

            if payment_option == 'in_store_full':
                try:
                    hire_booking = convert_temp_to_hire_booking(
                        temp_booking=temp_booking,
                        payment_method='in_store',
                        booking_payment_status='pending_in_store',
                        amount_paid_on_booking=Decimal('0.00'),
                        stripe_payment_intent_id=None,
                        payment_obj=None,
                    )
                    # Store the booking reference in the session for Step 7
                    request.session['final_booking_reference'] = hire_booking.booking_reference
                    messages.success(request, f"Your booking ({hire_booking.booking_reference}) has been successfully created. Please pay the full amount in-store at pickup.")
                    # Redirect to step 7 without payment_intent_id for in-store bookings
                    return redirect('hire:step7_confirmation')
                except Exception as e:
                    messages.error(request, "There was an error finalizing your in-store booking. Please try again.")
                    return redirect('hire:step5_summary_payment_options')
            elif payment_option == 'online_full' or payment_option == 'online_deposit':
                return redirect('hire:step6_payment_details')
            else:
                messages.error(request, "An invalid payment option was selected. Please try again.")
                return redirect('hire:step5_summary_payment_options')

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
