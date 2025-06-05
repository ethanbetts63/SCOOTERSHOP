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
        print(f"DEBUG: Step3CustomerMotorcycleView dispatch - Request path: {request.path}")
        temp_booking_uuid = request.session.get('temp_booking_uuid')
        print(f"DEBUG: temp_booking_uuid from session: {temp_booking_uuid}")

        if not temp_booking_uuid:
            print("DEBUG: No temp_booking_uuid found in session. Redirecting to service:service")
            return redirect(reverse('service:service'))

        try:
            self.temp_booking = TempServiceBooking.objects.get(session_uuid=temp_booking_uuid)
            print(f"DEBUG: TempBooking found: {self.temp_booking.session_uuid}")
        except TempServiceBooking.DoesNotExist:
            print(f"DEBUG: TempServiceBooking with UUID {temp_booking_uuid} does not exist. Popping from session and redirecting.")
            request.session.pop('temp_booking_uuid', None)
            return redirect(reverse('service:service'))

        self.service_settings = ServiceSettings.objects.first() 
        print(f"DEBUG: ServiceSettings loaded: {self.service_settings.pk if self.service_settings else 'None'}")

        # The default dispatch method will return None if no HTTPResponse is generated
        # at this stage, allowing the get/post method to be called.
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        print(f"DEBUG: Step3CustomerMotorcycleView GET method called. Temp Booking customer_motorcycle: {self.temp_booking.customer_motorcycle}")
        form = None
        if self.temp_booking.customer_motorcycle:
            form = CustomerMotorcycleForm(instance=self.temp_booking.customer_motorcycle)
        else:
            form = CustomerMotorcycleForm()

        context = {
            'form': form,
            'temp_booking': self.temp_booking,
            'other_brand_policy_text': self.service_settings.other_brand_policy_text if self.service_settings else "",
            'enable_service_brands': self.service_settings.enable_service_brands if self.service_settings else False,
            'step': 3,
            'total_steps': 7,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        print(f"DEBUG: Step3CustomerMotorcycleView POST method called. Is authenticated: {request.user.is_authenticated}")
        form = None
        motorcycle_instance = self.temp_booking.customer_motorcycle

        if motorcycle_instance:
            print(f"DEBUG: Editing existing motorcycle: {motorcycle_instance.pk}")
            form = CustomerMotorcycleForm(request.POST, request.FILES, instance=motorcycle_instance)
        else:
            print("DEBUG: Creating new motorcycle.")
            form = CustomerMotorcycleForm(request.POST, request.FILES)

        if form.is_valid():
            print("DEBUG: Form is valid.")
            customer_motorcycle = form.save(commit=False)
            
            # **FIX for authenticated user test:**
            # Associate the service_profile if the user is authenticated and a service_profile exists
            if request.user.is_authenticated and self.temp_booking.service_profile:
                customer_motorcycle.service_profile = self.temp_booking.service_profile
                print(f"DEBUG: Linked customer_motorcycle to service_profile: {self.temp_booking.service_profile.pk}")
            elif request.user.is_authenticated and not self.temp_booking.service_profile:
                # This case might happen if service_profile wasn't set earlier in the flow
                # For now, we'll let it be None, as the test for anonymous users expects None.
                # A more robust solution would ensure service_profile is always set for authenticated users
                # before reaching this step if it's a required link.
                print("DEBUG: Authenticated user but no service_profile found on temp_booking. customer_motorcycle.service_profile will be None.")


            customer_motorcycle.save()
            print(f"DEBUG: CustomerMotorcycle saved: {customer_motorcycle.pk}, Brand: {customer_motorcycle.brand}, Service Profile: {customer_motorcycle.service_profile}")


            self.temp_booking.customer_motorcycle = customer_motorcycle
            self.temp_booking.save()
            print(f"DEBUG: TempBooking {self.temp_booking.session_uuid} linked to CustomerMotorcycle {customer_motorcycle.pk}. Redirecting to service:service_book_step4")

            return redirect(reverse('service:service_book_step4'))
        else:
            print("DEBUG: Form is NOT valid. Errors:", form.errors)
            context = {
                'form': form,
                'temp_booking': self.temp_booking,
                'other_brand_policy_text': self.service_settings.other_brand_policy_text if self.service_settings else "",
                'enable_service_brands': self.service_settings.enable_service_brands if self.service_settings else False,
                'step': 3,
                'total_steps': 7,
            }
            return render(request, self.template_name, context)

