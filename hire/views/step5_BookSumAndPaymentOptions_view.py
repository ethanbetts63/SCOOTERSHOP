# hire/views/step5_BookSumAndPaymentOptions_view.py

from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from decimal import Decimal
from django.conf import settings # Import settings to access ADMIN_EMAIL

from ..models import TempHireBooking
from dashboard.models import HireSettings
from ..forms.step5_BookSumAndPaymentOptions_form import PaymentOptionForm
from ..utils import is_motorcycle_available # This utility is expected to add messages
from ..hire_pricing import calculate_booking_grand_total
from hire.temp_hire_converter import convert_temp_to_hire_booking

# Import the email sending utility
from mailer.utils import send_templated_email

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

        # Recalculate prices to ensure they are up-to-date
        calculated_prices = calculate_booking_grand_total(temp_booking, hire_settings)
        temp_booking.total_hire_price = calculated_prices['motorcycle_price']
        temp_booking.total_package_price = calculated_prices['package_price']
        temp_booking.total_addons_price = calculated_prices['addons_total_price']
        temp_booking.grand_total = calculated_prices['grand_total']
        temp_booking.deposit_amount = calculated_prices['deposit_amount'] # Updated to use calculated deposit
        temp_booking.currency = calculated_prices['currency'] # Updated to use calculated currency

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

            # Recalculate prices to ensure they are up-to-date before saving and proceeding
            calculated_prices = calculate_booking_grand_total(temp_booking, hire_settings)
            temp_booking.total_hire_price = calculated_prices['motorcycle_price']
            temp_booking.total_package_price = calculated_prices['package_price']
            temp_booking.total_addons_price = calculated_prices['addons_total_price']
            temp_booking.grand_total = calculated_prices['grand_total']
            temp_booking.deposit_amount = calculated_prices['deposit_amount'] # Updated to use calculated deposit
            temp_booking.currency = calculated_prices['currency'] # Updated to use calculated currency

            temp_booking.save()

            # The is_motorcycle_available function is expected to add the message itself.
            # Removing the redundant messages.error call here.
            if not is_motorcycle_available(request, temp_booking.motorcycle, temp_booking):
                return redirect('hire:step2_choose_bike')

            if payment_option == 'in_store_full':
                try:
                    hire_booking = convert_temp_to_hire_booking(
                        temp_booking=temp_booking,
                        payment_method='in_store_full',
                        booking_payment_status='unpaid',
                        amount_paid_on_booking=Decimal('0.00'),
                        stripe_payment_intent_id=None,
                        payment_obj=None,
                    )
                    # Store the booking reference in the session for Step 7
                    request.session['final_booking_reference'] = hire_booking.booking_reference
                    messages.success(request, f"Your booking ({hire_booking.booking_reference}) has been successfully created. Please pay the full amount in-store at pickup.")

                    # --- Email Sending for In-Store Booking Confirmation ---
                    # Context for email templates
                    email_context = {
                        'hire_booking': hire_booking,
                        'user': request.user if request.user.is_authenticated else None,
                        'driver_profile': hire_booking.driver_profile,
                        'is_in_store': True, # Flag for template logic if needed
                    }

                    # Send confirmation email to the user
                    user_email = hire_booking.driver_profile.user.email if hire_booking.driver_profile.user else hire_booking.driver_profile.email
                    if user_email:
                        send_templated_email(
                            recipient_list=[user_email],
                            subject=f"Your Motorcycle Hire Booking Confirmation - {hire_booking.booking_reference}",
                            template_name='booking_confirmation_user.html',
                            context=email_context,
                            user=request.user if request.user.is_authenticated else None,
                            driver_profile=hire_booking.driver_profile,
                            booking=hire_booking
                        )

                    # Send notification email to the admin
                    if settings.ADMIN_EMAIL:
                        send_templated_email(
                            recipient_list=[settings.ADMIN_EMAIL],
                            subject=f"New Motorcycle Hire Booking (In-Store) - {hire_booking.booking_reference}",
                            template_name='booking_confirmation_admin.html',
                            context=email_context,
                            booking=hire_booking
                        )
                    # --- End Email Sending ---

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
