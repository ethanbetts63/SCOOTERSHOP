                                   

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin                                         
from ..forms.add_addon_form import AddAddOnForm                  
from hire.models import AddOn                         

class AddEditAddOnView(LoginRequiredMixin, View):
    template_name = 'dashboard/add_edit_addon.html'                             
    form_class = AddAddOnForm

    def get(self, request, pk=None):
        if pk:
                                        
            addon = get_object_or_404(AddOn, pk=pk)
            form = self.form_class(instance=addon)
            title = f"Edit Add-On: {addon.name}"
        else:
                                 
            form = self.form_class()
            title = "Add New Hire Add-On"

        context = {
            'form': form,
            'title': title,
            'is_edit': pk is not None,
        }
        return render(request, self.template_name, context)

    def post(self, request, pk=None):
        if pk:
            addon = get_object_or_404(AddOn, pk=pk)
            form = self.form_class(request.POST, instance=addon)
            success_message = "Add-On updated successfully!"
        else:
            form = self.form_class(request.POST)
            success_message = "Add-On added successfully!"

        if form.is_valid():
            form.save()
            messages.success(request, success_message)
            return redirect('dashboard:settings_hire_addons')                            
        else:
                                                                      
            title = f"Edit Add-On: {addon.name}" if pk else "Add New Hire Add-On"
            messages.error(request, "Please correct the errors below.")
            context = {
                'form': form,
                'title': title,
                'is_edit': pk is not None,
            }
            return render(request, self.template_name, context)