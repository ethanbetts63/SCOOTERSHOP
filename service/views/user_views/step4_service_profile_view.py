from django.shortcuts import render, redirect
from django.views import View
from django.urls import reverse
from django.contrib import messages
from service.models import TempServiceBooking, ServiceProfile, ServiceFAQ
from service.forms.step4_service_profile_form import ServiceBookingUserForm

class Step4ServiceProfileView(View):
    template_name = 'service/step4_service_profile.html' 
    form_class = ServiceBookingUserForm

    def _get_temp_booking(self, request):
        temp_booking_uuid = request.session.get('temp_service_booking_uuid')
        if not temp_booking_uuid:
            messages.error(request, "Your booking session has expired or is invalid. Please start over.")
            return None, redirect(reverse('service:service'))

        try:
            temp_booking = TempServiceBooking.objects.select_related(
                'customer_motorcycle', 
                'service_profile'
            ).get(session_uuid=temp_booking_uuid)
            return temp_booking, None
        except TempServiceBooking.DoesNotExist:
            request.session.pop('temp_service_booking_uuid', None)
            messages.error(request, "Your booking session could not be found. Please start over.")
            return None, redirect(reverse('service:service'))

    def _get_service_profile_instance(self, request, temp_booking):
        if temp_booking and temp_booking.service_profile:
            return temp_booking.service_profile
        
        if request.user.is_authenticated:
            try:
                return request.user.service_profile
            except ServiceProfile.DoesNotExist:
                return None 
            except AttributeError:
                profile = ServiceProfile.objects.filter(user=request.user).first()
                return profile

        return None

    def dispatch(self, request, *args, **kwargs):
        self.temp_booking, redirect_response = self._get_temp_booking(request)
        if redirect_response:
            return redirect_response
        
        if not self.temp_booking.customer_motorcycle:
            messages.warning(request, "Please select or add your motorcycle details first (Step 3).")
            return redirect(reverse('service:service_book_step3'))
        
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        profile_instance = self._get_service_profile_instance(request, self.temp_booking)
        form = self.form_class(instance=profile_instance)
        service_faqs = ServiceFAQ.objects.filter(is_active=True)
        
        context = {
            'form': form,
            'temp_booking': self.temp_booking,
            'step': 4, 
            'total_steps': 7,
            'service_faqs': service_faqs,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        profile_instance = self._get_service_profile_instance(request, self.temp_booking)
        form = self.form_class(request.POST, instance=profile_instance)

        if form.is_valid():
            service_profile = form.save(commit=False)

            if request.user.is_authenticated and not service_profile.user_id:
                service_profile.user = request.user
            
            service_profile.save()

            self.temp_booking.service_profile = service_profile
            
            if self.temp_booking.customer_motorcycle:
                motorcycle = self.temp_booking.customer_motorcycle
                if motorcycle.service_profile != service_profile:
                    motorcycle.service_profile = service_profile
                    motorcycle.save(update_fields=['service_profile'])
            
            self.temp_booking.save(update_fields=['service_profile'])

            messages.success(request, "Your details have been saved successfully.")
            return redirect(reverse('service:service_book_step5'))
        else:
            messages.error(request, "Please correct the errors below.")
            service_faqs = ServiceFAQ.objects.filter(is_active=True)
            context = {
                'form': form,
                'temp_booking': self.temp_booking,
                'step': 4,
                'total_steps': 7, 
                'service_faqs': service_faqs,
            }
            return render(request, self.template_name, context)