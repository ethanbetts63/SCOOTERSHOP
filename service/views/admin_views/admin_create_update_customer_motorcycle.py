
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from service.forms import AdminCustomerMotorcycleForm 
from service.models import CustomerMotorcycle                                                            



class CustomerMotorcycleCreateUpdateView(LoginRequiredMixin, UserPassesTestMixin, View):
    
    template_name = 'service/admin_customer_motorcycle_create_update.html'               
    form_class = AdminCustomerMotorcycleForm

    def test_func(self):
        
        return self.request.user.is_staff or self.request.user.is_superuser

    def get(self, request, pk=None, *args, **kwargs):
        
        instance = None
        if pk:
                                                                                         
            instance = get_object_or_404(CustomerMotorcycle, pk=pk)
            form = self.form_class(instance=instance)                        
        else:
                                                                
            form = self.form_class()

        context = {
            'form': form,
            'is_edit_mode': bool(pk),                                     
            'current_motorcycle': instance                                                     
        }
        return render(request, self.template_name, context)

    def post(self, request, pk=None, *args, **kwargs):
        
        instance = None
        if pk:
            instance = get_object_or_404(CustomerMotorcycle, pk=pk)
                                                              
            form = self.form_class(request.POST, request.FILES, instance=instance)
        else:
                                                     
            form = self.form_class(request.POST, request.FILES)

        if form.is_valid():
            customer_motorcycle = form.save()
            if pk:
                messages.success(request, f"Motorcycle '{customer_motorcycle}' updated successfully.")
            else:
                messages.success(request, f"Motorcycle '{customer_motorcycle}' created successfully.")
                                                                                        
            return redirect(reverse('service:admin_customer_motorcycle_management'))
        else:
            messages.error(request, "Please correct the errors below.")
            context = {
                'form': form,                                 
                'is_edit_mode': bool(pk),
                'current_motorcycle': instance
            }
            return render(request, self.template_name, context)
