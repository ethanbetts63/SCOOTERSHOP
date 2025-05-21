# hire/views/step5_BookSumAndPaymentOptions_view.py

from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages

from ..models import TempHireBooking
from dashboard.models import HireSettings
from ..forms.step5_BookSumAndPaymentOptions_form import PaymentOptionForm
from ..views.utils import calculate_hire_duration_days

class BookSumAndPaymentOptionsView(View):
    template_name = 'hire/step5_book_sum_and_payment_options.html'

    def get(self, request, *args, **kwargs):
        temp_booking = self._get_temp_booking(request)
        if not temp_booking:
            messages.error(request, "Your booking session has expired. Please start again.")
            return redirect('hire:step1_select_datetime')

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
            return redirect('hire:step1_select_datetime')

        hire_settings = HireSettings.objects.first()
        if not hire_settings:
            messages.error(request, "Hire settings not found.")
            return redirect('home') # Or some appropriate error page

        form = PaymentOptionForm(request.POST, temp_booking=temp_booking, hire_settings=hire_settings)

        if form.is_valid():
            payment_method = form.cleaned_data['payment_method']
            temp_booking.payment_method = payment_method
            temp_booking.save()

            # Redirect to the next step based on the payment method
            if payment_method == 'online_full' or payment_method == 'online_deposit':
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

