                                                             

from django.urls import reverse_lazy
from django.views.generic import UpdateView
from django.contrib import messages
from django.forms import ValidationError
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import user_passes_test

from payments.models import RefundPolicySettings
from payments.forms.refund_settings_form import RefundSettingsForm
from users.views.auth import is_admin                                               


@method_decorator(user_passes_test(is_admin), name='dispatch')
class AdminRefundSettingsView(UpdateView):
    
    model = RefundPolicySettings
    form_class = RefundSettingsForm
    template_name = 'payments/admin_refund_settings.html'
                                                                            
    success_url = reverse_lazy('payments:admin_refund_settings')

    def get_object(self, queryset=None):
        
                                                                        
        obj, created = RefundPolicySettings.objects.get_or_create(pk=1)
        return obj

    def form_valid(self, form):
        
        try:
            response = super().form_valid(form)
            messages.success(self.request, "Refund Policy settings updated successfully!")
            return response
        except ValidationError as e:
                                                                                                      
            form.add_error(None, e)
            return self.form_invalid(form)

    def form_invalid(self, form):
        
        messages.error(self.request, "There was an error updating refund policy settings. Please correct the errors below.")
        return super().form_invalid(form)

    def post(self, request, *args, **kwargs):
        
        if 'refund_policy_settings_submit' in request.POST:
            self.object = self.get_object()                                                   
            form = self.get_form()
            if form.is_valid():
                return self.form_valid(form)
            else:
                return self.form_invalid(form)
        return super().post(request, *args, **kwargs)                                                         
