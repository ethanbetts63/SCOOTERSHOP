from django.shortcuts import render, redirect
from django.views import View
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal # Import Decimal for monetary values

from service.forms.step5_payment_choice_and_terms_form import PaymentOptionForm
from service.models import TempServiceBooking, ServiceSettings
from service.utils.convert_temp_service_booking import convert_temp_service_booking # Import the utility function

class Step5PaymentDropoffAndTermsView(View):
    template_name = 'service/step5_payment_dropoff_and_terms.html'
    form_class = PaymentOptionForm

    def _get_temp_booking(self, request):
        temp_service_booking_uuid = request.session.get('temp_service_booking_uuid')
        if not temp_service_booking_uuid:
            messages.error(request, "Your booking session has expired. Please start over.")
            return None, redirect(reverse('service:service'))
        
        try:
            temp_booking = TempServiceBooking.objects.select_related(
                'service_type', 'customer_motorcycle', 'service_profile'
            ).get(session_uuid=temp_service_booking_uuid)
            return temp_booking, None
        except TempServiceBooking.DoesNotExist:
            request.session.pop('temp_service_booking_uuid', None)
            messages.error(request, "Your booking session could not be found. Please start over.")
            return None, redirect(reverse('service:service'))

    def dispatch(self, request, *args, **kwargs):
        self.temp_booking, redirect_response = self._get_temp_booking(request)
        if redirect_response:
            return redirect_response

        if not self.temp_booking.service_profile:
            messages.warning(request, "Please complete your personal details first (Step 4).")
            return redirect(reverse('service:service_book_step4'))

        self.service_settings = ServiceSettings.objects.first()
        if not self.service_settings:
            messages.error(request, "Service settings are not configured. Please contact an administrator.")
            return redirect(reverse('service:service'))
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = {
            'service_settings': self.service_settings,
            'temp_booking': self.temp_booking,
        }
        return kwargs

    def get_context_data(self, **kwargs):
        today = timezone.localdate(timezone.now())
        service_date = self.temp_booking.service_date
        max_advance_days = self.service_settings.max_advance_dropoff_days
        
        is_same_day_dropoff_only = (max_advance_days == 0)

        max_dropoff_date = service_date
        
        min_dropoff_date = service_date - timedelta(days=max_advance_days)

        if min_dropoff_date < today:
            min_dropoff_date = today

        context = {
            'temp_booking': self.temp_booking,
            'service_settings': self.service_settings,
            'min_dropoff_date': min_dropoff_date.strftime('%Y-%m-%d'),
            'max_dropoff_date': max_dropoff_date.strftime('%Y-%m-%d'),
            'get_times_url': reverse('service:get_available_times_for_date'),
            'step': 5,
            'total_steps': 7,
            'is_same_day_dropoff_only': is_same_day_dropoff_only,
        }
        context.update(kwargs)
        return context

    def get(self, request, *args, **kwargs):
        initial_data = {
            'dropoff_date': self.temp_booking.dropoff_date,
            'dropoff_time': self.temp_booking.dropoff_time,
            'payment_option': self.temp_booking.payment_option,
        }
        
        if self.service_settings.max_advance_dropoff_days == 0:
            initial_data['dropoff_date'] = self.temp_booking.service_date

        form = self.form_class(initial=initial_data, **self.get_form_kwargs())
        
        context = self.get_context_data(form=form)
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        print(f"DEBUG: Step5 - POST request received.")
        form = self.form_class(request.POST, **self.get_form_kwargs())

        if form.is_valid():
            self.temp_booking.dropoff_date = form.cleaned_data['dropoff_date']
            self.temp_booking.dropoff_time = form.cleaned_data['dropoff_time']
            self.temp_booking.payment_option = form.cleaned_data['payment_option']
            
            print(f"DEBUG: Step5 - Form is valid. Cleaned payment_option: {form.cleaned_data['payment_option']}")
            
            # Save TempBooking first to ensure dropoff_date, dropoff_time, and payment_option are persisted
            self.temp_booking.save(update_fields=['dropoff_date', 'dropoff_time', 'payment_option'])
            print(f"DEBUG: Step5 - TempBooking saved. Stored payment_option: {self.temp_booking.payment_option}")

            messages.success(request, "Drop-off and payment details have been saved successfully.")
            
            # Conditional redirect based on payment option
            if self.temp_booking.payment_option == 'in_store_full':
                print("DEBUG: Step5 - 'in_store_full' payment selected. Finalizing booking directly.")
                try:
                    # Call convert_temp_service_booking to create the final ServiceBooking
                    # For in-store payment, amount_paid is 0 and status is 'unpaid'
                    final_service_booking = convert_temp_service_booking(
                        temp_booking=self.temp_booking,
                        payment_method=self.temp_booking.payment_option, # 'in_store_full'
                        booking_payment_status='unpaid', # Initial status for in-store payment
                        amount_paid_on_booking=Decimal('0.00'),
                        calculated_total_on_booking=self.temp_booking.service_type.base_price, # Or actual calculated total
                        stripe_payment_intent_id=None, # No Stripe intent for in-store
                        payment_obj=None, # No Payment object associated initially
                    )
                    request.session['final_service_booking_reference'] = final_service_booking.service_booking_reference
                    print(f"DEBUG: Step5 - Booking finalized. Redirecting to Step 7 with booking reference: {final_service_booking.service_booking_reference}")
                    return redirect(reverse('service:service_book_step7'))

                except Exception as e:
                    print(f"DEBUG: Step5 - ERROR finalizing in-store booking: {e}")
                    messages.error(request, f"An error occurred while finalizing your booking: {e}. Please try again.")
                    # If an error occurs, you might want to redirect back to step 5 or a general error page
                    return redirect(reverse('service:service_book_step5'))
            else:
                print("DEBUG: Step5 - Redirecting to service_book_step6 (Online payment selected).")
                return redirect(reverse('service:service_book_step6'))

        else:
            print(f"DEBUG: Step5 - Form is NOT valid. Errors: {form.errors}")
            messages.error(request, "Please correct the errors highlighted below.")
            context = self.get_context_data(form=form)
            return render(request, self.template_name, context)
