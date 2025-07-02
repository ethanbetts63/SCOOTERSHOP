                                          

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
                                                                                             

                    
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

                                                      
from service.forms import AdminServiceProfileForm
from service.models import ServiceProfile

class ServiceProfileManagementView(LoginRequiredMixin, UserPassesTestMixin, View):
    
    template_name = 'service/admin_service_profile_management.html'
    form_class = AdminServiceProfileForm
    paginate_by = 10                                                                       

    def test_func(self):
        
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_profiles_for_display(self):
        
        return ServiceProfile.objects.all().order_by('-created_at')

    def get_context_data(self, **kwargs):
        
        context = {}
        
                                          
        pk = kwargs.get('pk')
        instance = None
        is_edit_mode = False

        if pk:
            instance = get_object_or_404(ServiceProfile, pk=pk)
            form = self.form_class(instance=instance)
            is_edit_mode = True
        else:
            form = self.form_class()

                                                                             
        profile_list = self.get_profiles_for_display()
        paginator = Paginator(profile_list, self.paginate_by)
        page = self.request.GET.get('page')

        try:
            profiles_page = paginator.page(page)
        except PageNotAnInteger:
                                                            
            profiles_page = paginator.page(1)
        except EmptyPage:
                                                                                
            profiles_page = paginator.page(paginator.num_pages)

        context.update({
            'profiles': profiles_page,                                          
            'page_obj': profiles_page,                                                                   
            'is_paginated': profiles_page.has_other_pages(),                                
            'form': form,
            'is_edit_mode': is_edit_mode,
            'current_profile': instance,
            'search_term': self.request.GET.get('q', '')                                                
        })
        return context

    def get(self, request, pk=None, *args, **kwargs):
        
        context = self.get_context_data(pk=pk)
        return render(request, self.template_name, context)

    def post(self, request, pk=None, *args, **kwargs):
        
        instance = None
        if pk:
            instance = get_object_or_404(ServiceProfile, pk=pk)
            form = self.form_class(request.POST, instance=instance)
        else:
            form = self.form_class(request.POST)

        if form.is_valid():
            service_profile = form.save()
            if pk:
                messages.success(request, f"Service Profile for '{service_profile.name}' updated successfully.")
            else:
                messages.success(request, f"Service Profile for '{service_profile.name}' created successfully.")
                                                                                   
            return redirect(reverse('service:admin_service_profiles'))
        else:
            messages.error(request, "Please correct the errors below.")
                                                                 
                                                                                            
            context = self.get_context_data(pk=pk)
            context['form'] = form                                                
            return render(request, self.template_name, context)

