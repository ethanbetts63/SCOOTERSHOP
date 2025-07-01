                                                   

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from service.forms import AdminServiceTypeForm                                  
from service.models import ServiceType                               

class ServiceTypeCreateUpdateView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    Admin view for creating a new ServiceType or updating an existing one.
    Requires the user to be logged in and a staff member or superuser.
    """
    template_name = 'service/admin_service_type_create_update.html'                                             
    form_class = AdminServiceTypeForm

    def test_func(self):
        """
        Ensures that only staff members or superusers can access this view.
        """
        return self.request.user.is_staff or self.request.user.is_superuser

    def get(self, request, pk=None, *args, **kwargs):
        """
        Handles GET requests to display the form for creating a new service type
        or editing an existing one.
        """
        instance = None
        if pk:
                                                                                           
            instance = get_object_or_404(ServiceType, pk=pk)
            form = self.form_class(instance=instance)                        
        else:
                                                                
            form = self.form_class()

        context = {
            'form': form,
            'is_edit_mode': bool(pk),                                     
            'current_service_type': instance                                                       
        }
        return render(request, self.template_name, context)

    def post(self, request, pk=None, *args, **kwargs):
        """
        Handles POST requests for form submission (creating or updating a ServiceType).
        """
        instance = None
        if pk:
            instance = get_object_or_404(ServiceType, pk=pk)
            form = self.form_class(request.POST, request.FILES, instance=instance)                                             
        else:
            form = self.form_class(request.POST, request.FILES)                                             

        if form.is_valid():
            service_type = form.save()
            if pk:
                messages.success(request, f"Service Type '{service_type.name}' updated successfully.")
            else:
                messages.success(request, f"Service Type '{service_type.name}' created successfully.")
                                                                             
            return redirect(reverse('service:service_types_management'))
        else:
            messages.error(request, "Please correct the errors below.")
            context = {
                'form': form,                                 
                'is_edit_mode': bool(pk),
                'current_service_type': instance
            }
            return render(request, self.template_name, context)

