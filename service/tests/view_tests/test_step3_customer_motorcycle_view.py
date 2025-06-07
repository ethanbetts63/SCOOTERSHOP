from django.shortcuts import render, redirect
from django.views import View
from django.urls import reverse
from django.conf import settings
import uuid

from service.models import TempServiceBooking, CustomerMotorcycle, ServiceProfile, ServiceSettings
from service.forms.step3_customer_motorcycle_form import CustomerMotorcycleForm


class Step3CustomerMotorcycleView(View):
    template_name = 'service/step3_customer_motorcycle.html'

    def dispatch(self, request, *args, **kwargs):
        print(f"DEBUG: Entering {self.__class__.__name__} dispatch method.")
        temp_booking_uuid = request.session.get('temp_service_booking_uuid')
        print(f"DEBUG: {self.__class__.__name__} dispatch: Session UUID: {temp_booking_uuid}")


        if not temp_booking_uuid:
            print(f"DEBUG: {self.__class__.__name__} dispatch: No UUID in session. Redirecting to service:service.")
            return redirect(reverse('service:service'))

        try:
            self.temp_booking = TempServiceBooking.objects.get(session_uuid=temp_booking_uuid)
            print(f"DEBUG: {self.__class__.__name__} dispatch: Successfully retrieved TempServiceBooking.")
        except TempServiceBooking.DoesNotExist:
            request.session.pop('temp_service_booking_uuid', None)
            print(f"DEBUG: {self.__class__.__name__} dispatch: TempServiceBooking not found for UUID. Redirecting to service:service.")
            return redirect(reverse('service:service'))

        self.service_settings = ServiceSettings.objects.first() 
        if not self.service_settings:
            messages.error(request, "Service settings are not configured. Please contact an administrator.")
            print(f"ERROR: {self.__class__.__name__} dispatch: ServiceSettings not found. Redirecting to service:service.")
            return redirect(reverse('service:service'))

        print(f"DEBUG: {self.__class__.__name__} dispatch: All dispatch checks passed. Proceeding.")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        print(f"DEBUG: Entering {self.__class__.__name__} GET method.")
        form = None
        if self.temp_booking.customer_motorcycle:
            print(f"DEBUG: {self.__class__.__name__} GET: TempBooking has customer_motorcycle. Prefilling form.")
            form = CustomerMotorcycleForm(instance=self.temp_booking.customer_motorcycle)
        else:
            print(f"DEBUG: {self.__class__.__name__} GET: TempBooking has NO customer_motorcycle. Rendering blank form.")
            form = CustomerMotorcycleForm()

        context = {
            'form': form,
            'temp_booking': self.temp_booking,
            'other_brand_policy_text': self.service_settings.other_brand_policy_text if self.service_settings else "",
            'enable_service_brands': self.service_settings.enable_service_brands if self.service_settings else False,
            'step': 3,
            'total_steps': 7,
        }
        print(f"DEBUG: {self.__class__.__name__} GET: Rendering template.")
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        print(f"DEBUG: Entering {self.__class__.__name__} POST method.")
        form = None
        motorcycle_instance = self.temp_booking.customer_motorcycle

        if motorcycle_instance:
            print(f"DEBUG: {self.__class__.__name__} POST: TempBooking has customer_motorcycle. Updating existing.")
            form = CustomerMotorcycleForm(request.POST, request.FILES, instance=motorcycle_instance)
        else:
            print(f"DEBUG: {self.__class__.__name__} POST: TempBooking has NO customer_motorcycle. Creating new.")
            form = CustomerMotorcycleForm(request.POST, request.FILES)

        if form.is_valid():
            print(f"DEBUG: {self.__class__.__name__} POST: Form is valid.")
            customer_motorcycle = form.save(commit=False)
            
            if request.user.is_authenticated and self.temp_booking.service_profile:
                customer_motorcycle.service_profile = self.temp_booking.service_profile
                print(f"DEBUG: {self.__class__.__name__} POST: Linking motorcycle to authenticated user's ServiceProfile.")

            customer_motorcycle.save()
            print(f"DEBUG: {self.__class__.__name__} POST: CustomerMotorcycle saved. ID: {customer_motorcycle.pk}")


            self.temp_booking.customer_motorcycle = customer_motorcycle
            self.temp_booking.save()
            print(f"DEBUG: {self.__class__.__name__} POST: TempBooking updated with new customer_motorcycle. Redirecting to service:service_book_step4.")

            return redirect(reverse('service:service_book_step4'))
        else:
            print(f"DEBUG: {self.__class__.__name__} POST: Form is NOT valid. Errors: {form.errors}")
            context = {
                'form': form,
                'temp_booking': self.temp_booking,
                'other_brand_policy_text': self.service_settings.other_brand_policy_text if self.service_settings else "",
                'enable_service_brands': self.service_settings.enable_service_brands if self.service_settings else False,
                'step': 3,
                'total_steps': 7,
            }
            print(f"DEBUG: {self.__class__.__name__} POST: Re-rendering form with errors.")
            return render(request, self.template_name, context)
